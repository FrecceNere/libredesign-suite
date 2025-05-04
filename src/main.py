import webview
from flask import Flask, render_template
import subprocess
import platform
import json
import sys
import os
import shutil
import requests
from pathlib import Path
import tempfile

app = Flask(__name__,
    template_folder='frontend/templates',
    static_folder='frontend/static')

class Api:
    def get_programs(self):
        """Return list of available open source programs"""
        programs = {
            'image_editing': [
                {
                    'name': 'GIMP',
                    'description': 'GNU Image Manipulation Program',
                    'category': 'Photo Editing',
                    'logo': '/static/img/logos/gimp.png',
                    'variants': [
                        {'name': 'Standard GIMP', 'type': 'apt'},
                        {'name': 'PhotoGIMP', 'type': 'flatpak+patch'}
                    ]
                },
                {
                    'name': 'Inkscape',
                    'description': 'Vector Graphics Editor',
                    'category': 'Vector Graphics',
                    'logo': '/static/img/logos/inkscape.png'
                },
            ],
            'video_editing': [
                {
                    'name': 'Kdenlive',
                    'description': 'Non-linear video editor',
                    'category': 'Video Editing',
                    'logo': '/static/img/logos/kdenlive.png'
                },
                {
                    'name': 'OpenShot',
                    'description': 'Video Editor',
                    'category': 'Video Editing',
                    'logo': '/static/img/logos/openshot.png'
                },
            ],
            'audio_editing': [
                {
                    'name': 'Audacity',
                    'description': 'Audio Editor and Recorder',
                    'category': 'Audio Editing',
                    'logo': '/static/img/logos/audacity.png'
                },
            ]
        }
        return programs

    def install_program(self, program_name, variant='apt'):
        """Handle program installation"""
        system = platform.system().lower()
        
        if system != 'linux':
            return {'success': False, 'message': 'Unsupported operating system'}

        try:
            if program_name == 'GIMP' and variant == 'flatpak+patch':
                return self._install_photogimp()
            else:
                package = self.package_managers['linux'][program_name]
                subprocess.run(['sudo', 'apt-get', 'install', '-y', package], check=True)
                return {'success': True, 'message': f'{program_name} installed successfully'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def _install_photogimp(self):
        """Install GIMP via Flatpak and apply PhotoGIMP patch"""
        try:
            # Install Flatpak if not present
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'flatpak'], check=True)
            subprocess.run(['flatpak', 'remote-add', '--if-not-exists', 'flathub', 
                          'https://flathub.org/repo/flathub.flatpakrepo'], check=True)
            
            # Install GIMP via Flatpak
            subprocess.run(['flatpak', 'install', '-y', 'flathub', 'org.gimp.GIMP'], check=True)
            
            # Download and apply PhotoGIMP patch
            home = Path.home()
            config_dir = home / '.var/app/org.gimp.GIMP/config'
            
            # Create temp directory for download
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Download PhotoGIMP
                url = "https://github.com/Diolinux/PhotoGIMP/archive/refs/heads/master.zip"
                zip_path = Path(tmp_dir) / "photogimp.zip"
                
                response = requests.get(url)
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract and copy files
                shutil.unpack_archive(zip_path, tmp_dir)
                photogimp_dir = Path(tmp_dir) / "PhotoGIMP-master"
                
                # Ensure config directory exists
                config_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy PhotoGIMP files
                if (photogimp_dir / '.config/GIMP').exists():
                    shutil.copytree(photogimp_dir / '.config/GIMP', config_dir / 'GIMP', 
                                  dirs_exist_ok=True)
                
            return {'success': True, 'message': 'PhotoGIMP installed successfully'}
            
        except Exception as e:
            return {'success': False, 'message': f'Error installing PhotoGIMP: {str(e)}'}

@app.route('/')
def index():
    return render_template('index.html')

def main():
    try:
        api = Api()
        window = webview.create_window('LibreDesign Suite', app, js_api=api)
        
        # Try to determine best GUI toolkit
        if platform.system() == 'Linux':
            gui_toolkit = None
            try:
                import PyQt6
                gui_toolkit = 'qt'
            except ImportError:
                try:
                    from gi import require_version
                    require_version('Gtk', '3.0')
                    require_version('WebKit2', '4.1')
                    gui_toolkit = 'gtk'
                except (ImportError, ValueError):
                    pass
            
            if gui_toolkit:
                webview.start(gui=gui_toolkit)
            else:
                raise Exception("Neither QT nor GTK toolkit available")
        else:
            webview.start()
            
    except Exception as e:
        print(f"Error starting application: {e}")
        print("Please make sure you have installed all required dependencies:")
        print("Run ./setup.sh to install all dependencies")
        sys.exit(1)

if __name__ == '__main__':
    main()
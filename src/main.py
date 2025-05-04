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
    def __init__(self):
        self.package_managers = {
            'linux': {
                'GIMP': 'gimp',
                'Inkscape': 'inkscape',
                'Kdenlive': 'kdenlive',
                'OpenShot': 'openshot-qt',
                'Audacity': 'audacity'
            }
        }

    def _check_flatpak_installed(self, app_id):
        """Check if a Flatpak application is installed"""
        try:
            result = subprocess.run(['flatpak', 'list', '--app', '--columns=application'],
                                 capture_output=True, text=True)
            return app_id in result.stdout
        except Exception:
            return False

    def _check_apt_installed(self, package_name):
        """Check if an apt package is installed"""
        try:
            result = subprocess.run(['dpkg', '-l', package_name],
                                 capture_output=True, text=True)
            return f"ii  {package_name}" in result.stdout
        except Exception:
            return False

    def _check_custom_config(self, program):
        """Check if custom configuration exists"""
        home = Path.home()
        if program == 'GIMP':
            config_path = home / '.var/app/org.gimp.GIMP/config/GIMP/2.10'
            return config_path.exists()
        elif program == 'Inkscape':
            config_path = home / '.var/app/org.inkscape.Inkscape/config/inkscape'
            preferences = config_path / 'preferences.xml'
            return preferences.exists() and preferences.is_file()
        return False

    def get_programs(self):
        """Return list of available open source programs with installation status"""
        programs = {
            'image_editing': [
                {
                    'name': 'GIMP',
                    'description': 'GNU Image Manipulation Program',
                    'category': 'Photo Editing',
                    'logo': '/static/img/logos/gimp.png',
                    'isCustomized': True,
                    'customDescription': 'Available with PhotoGIMP patch for Photoshop-like experience',
                    'variants': [
                        {
                            'name': 'Standard GIMP',
                            'type': 'apt',
                            'installed': self._check_apt_installed('gimp')
                        },
                        {
                            'name': 'PhotoGIMP',
                            'type': 'flatpak+patch',
                            'installed': self._check_flatpak_installed('org.gimp.GIMP') and 
                                       self._check_custom_config('GIMP')
                        }
                    ]
                },
                {
                    'name': 'Inkscape',
                    'description': 'Vector Graphics Editor',
                    'category': 'Vector Graphics',
                    'logo': '/static/img/logos/inkscape.png',
                    'isCustomized': True,
                    'customDescription': 'Available with Inkustrator patch for Illustrator-like experience',
                    'variants': [
                        {
                            'name': 'Standard Inkscape',
                            'type': 'apt',
                            'installed': self._check_apt_installed('inkscape')
                        },
                        {
                            'name': 'Inkustrator',
                            'type': 'flatpak+inkustrator',
                            'installed': self._check_flatpak_installed('org.inkscape.Inkscape') and 
                                       self._check_custom_config('Inkscape')
                        }
                    ]
                }
            ],
            'video_editing': [
                {
                    'name': 'Kdenlive',
                    'description': 'Non-linear video editor',
                    'category': 'Video Editing',
                    'logo': '/static/img/logos/kdenlive.png',
                    'installed': self._check_apt_installed('kdenlive')
                },
                {
                    'name': 'OpenShot',
                    'description': 'Video Editor',
                    'category': 'Video Editing',
                    'logo': '/static/img/logos/openshot.png',
                    'installed': self._check_apt_installed('openshot-qt')
                }
            ],
            'audio_editing': [
                {
                    'name': 'Audacity',
                    'description': 'Audio Editor and Recorder',
                    'category': 'Audio Editing',
                    'logo': '/static/img/logos/audacity.png',
                    'installed': self._check_apt_installed('audacity')
                }
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
            elif program_name == 'Inkscape' and variant == 'flatpak+inkustrator':
                return self._install_inkustrator()
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

    def _install_inkustrator(self):
        """Install Inkscape via Flatpak and apply Inkustrator patch"""
        try:
            # Install Flatpak if not present
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'flatpak'], check=True)
            subprocess.run(['flatpak', 'remote-add', '--if-not-exists', 'flathub', 
                          'https://flathub.org/repo/flathub.flatpakrepo'], check=True)
            
            # Install Inkscape via Flatpak
            subprocess.run(['flatpak', 'install', '-y', 'flathub', 'org.inkscape.Inkscape'], check=True)
            
            # Setup paths
            home = Path.home()
            inkscape_config = home / '.var/app/org.inkscape.Inkscape/config/inkscape'
            inkscape_share = home / '.var/app/org.inkscape.Inkscape/config/inkscape-extension-manager/extensions'
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                
                # Download Inkustrator
                url = "https://github.com/lucasgabmoreno/inkustrator/releases/download/1.3.2-1.0/inkustrator-1.3.2-1.0.zip"
                zip_path = tmp_path / "inkustrator.zip"
                
                print("Downloading Inkustrator...")
                response = requests.get(url)
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract everything
                print("Extracting files...")
                shutil.unpack_archive(zip_path, tmp_path)
                inkustrator_dir = tmp_path / "inkustrator-1.3.2-1.0"
                
                # Create necessary directories
                inkscape_config.mkdir(parents=True, exist_ok=True)
                inkscape_share.mkdir(parents=True, exist_ok=True)
                
                print("Installing Inkustrator files...")
                
                # Copy configuration files
                if (inkustrator_dir / 'preferences.xml').exists():
                    shutil.copy2(inkustrator_dir / 'preferences.xml', inkscape_config)
                
                # Copy keyboard shortcuts
                if (inkustrator_dir / 'keys').exists():
                    shutil.copy2(inkustrator_dir / 'keys', inkscape_config)
                
                # Copy all extensions and resources
                for item in inkustrator_dir.glob('*'):
                    if item.is_dir() and item.name not in ['preferences.xml', 'keys']:
                        # Copy directories (extensions, symbols, templates, etc.)
                        shutil.copytree(item, inkscape_share / item.name, 
                                      dirs_exist_ok=True)
                    elif item.is_file() and item.suffix in ['.py', '.inx', '.svg']:
                        # Copy extension files
                        shutil.copy2(item, inkscape_share)
                
                print("Inkustrator installation complete!")
                return {'success': True, 'message': 'Inkustrator installed successfully'}
                
        except Exception as e:
            return {'success': False, 'message': f'Error installing Inkustrator: {str(e)}'}

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
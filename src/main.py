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
import time
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

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
        self._cache = {
            'flatpak': {},
            'apt': {},
            'custom_config': {}
        }
        self._cache_ttl = 300  # 5 minutes cache validity

    def _cache_get(self, cache_type, key):
        cache_entry = self._cache[cache_type].get(key)
        if cache_entry:
            timestamp, value = cache_entry
            if time.time() - timestamp < self._cache_ttl:
                return value
        return None

    def _cache_set(self, cache_type, key, value):
        self._cache[cache_type][key] = (time.time(), value)

    def _check_flatpak_installed(self, app_id):
        """Check if a Flatpak application is installed"""
        cached = self._cache_get('flatpak', app_id)
        if cached is not None:
            return cached

        try:
            result = subprocess.run(['flatpak', 'list', '--app', '--columns=application'],
                                 capture_output=True, text=True)
            is_installed = app_id in result.stdout
            self._cache_set('flatpak', app_id, is_installed)
            return is_installed
        except Exception:
            return False

    def _check_apt_installed(self, package_name):
        """Check if an apt package is installed"""
        cached = self._cache_get('apt', package_name)
        if cached is not None:
            return cached

        try:
            result = subprocess.run(['dpkg', '-l', package_name],
                                 capture_output=True, text=True)
            is_installed = f"ii  {package_name}" in result.stdout
            self._cache_set('apt', package_name, is_installed)
            return is_installed
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

    def _download_file(self, url, destination):
        """Download file with progress and chunked transfer"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(block_size):
                    if chunk:
                        f.write(chunk)
            
            return True
        except Exception as e:
            print(f"Download error: {e}")
            return False

    def _parallel_copy(self, src_items, dst_base):
        """Copy files and directories in parallel"""
        def copy_item(item):
            dst_path = dst_base / item.name
            if item.is_dir():
                shutil.copytree(item, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst_path)

        max_workers = min(multiprocessing.cpu_count() * 2, len(src_items))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(copy_item, src_items))

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
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                zip_path = tmp_path / "photogimp.zip"
                
                # Download PhotoGIMP using optimized downloader
                print("Downloading PhotoGIMP...")
                url = "https://github.com/Diolinux/PhotoGIMP/releases/download/3.0/PhotoGIMP-linux.zip"
                if not self._download_file(url, zip_path):
                    raise Exception("Failed to download PhotoGIMP")
                
                print("Extracting files...")
                shutil.unpack_archive(zip_path, tmp_path)
                
                home = Path.home()
                extracted_dir = next(tmp_path.glob('PhotoGIMP*'))
                
                print("Installing PhotoGIMP files...")
                
                # Use parallel copy for better performance
                config_items = list((extracted_dir / '.config').glob('*'))
                local_items = list((extracted_dir / '.local').glob('*'))
                
                if config_items:
                    self._parallel_copy(config_items, home / '.config')
                if local_items:
                    self._parallel_copy(local_items, home / '.local')
                
                print("PhotoGIMP installation complete!")
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
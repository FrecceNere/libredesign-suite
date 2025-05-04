#!/bin/bash

echo "Setting up LibreDesign Suite..."

# Install system dependencies for PyGObject and QT
sudo apt-get update
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-webkit2-4.1 \
    libgirepository1.0-dev \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    gobject-introspection \
    libgtk-3-dev \
    qt6-base-dev \
    qt6-webengine-dev \
    python3-pyqt6 \
    python3-pyqt6.qtwebengine

# Create virtual environment if it doesn't exist
if [ ! -d "libredesign" ]; then
    python3 -m venv libredesign
fi

# Activate virtual environment
source libredesign/bin/activate

# Install Python packages
pip install --upgrade pip wheel setuptools
pip install flask
pip install "pywebview[qt]"

echo "Setup complete! You can now run the application with:"
echo "source libredesign/bin/activate"
echo "python src/main.py"
#!/bin/bash
# Build script for the Job Application Bot GUI

echo "Building the Job Application Bot executable..."

pyinstaller --onefile --windowed --name="JobApp" --icon="assets/icon.ico" gui_app.py

echo "Build complete. The executable can be found in the 'dist/' directory."

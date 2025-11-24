#!/bin/bash
# Build script for the Job Application Bot GUI

echo "Building the Job Application Bot executable..."

ICON_FLAG=""
if [[ "$(uname)" == "Darwin" ]]; then
    ICON_FLAG="--icon=assets/icon.icns"
fi

pyinstaller --onefile --windowed --name="JobApp" $ICON_FLAG --hidden-import=pkg_resources.extern gui_app.py

echo "Build complete. The executable can be found in the 'dist/' directory."

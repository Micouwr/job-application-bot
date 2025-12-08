#!/usr/bin/env python3
"""JobApplicationBot Standalone Builder
Builds a PyInstaller bundle with hidden imports and proper configuration."""

import os
import shutil
import sys
from pathlib import Path
import subprocess

# Project root
ROOT_DIR = Path(__file__).parent
GUI_SCRIPT = ROOT_DIR / "gui" / "tkinter_app.py"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"

def check_environment():
    """Verify build environment has all required tools."""
    print("🔍 Verifying build environment...")
    print("=" * 60)
    
    # Check Python
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found")
        print("Install with: pip install pyinstaller")
        return False
    
    # Check Pillow
    try:
        import PIL
        print("✅ Pillow (for icon conversion)")
    except ImportError:
        print("❌ Pillow not found")
        print("Install with: pip install Pillow")
        return False
    
    # Check GUI script
    if GUI_SCRIPT.exists():
        print(f"✅ Main GUI script found: {GUI_SCRIPT}")
    else:
        print(f"❌ GUI script not found: {GUI_SCRIPT}")
        return False
    
    # Check .env
    if (ROOT_DIR / ".env").exists():
        print("✅ .env configuration file found (Will NOT be bundled)")
    else:
        print("⚠️  .env file not found (users must provide their own)")
    
    # Check icons
    windows_icon = ROOT_DIR / "assets" / "icon.ico"
    macos_icon = ROOT_DIR / "assets" / "icon.icns"
    
    print("   Icon Files:")
    if windows_icon.exists():
        print(f"✅    - Windows icon: {windows_icon} ({windows_icon.stat().st_size} bytes)")
    if macos_icon.exists():
        print(f"✅    - macOS icon: {macos_icon} ({macos_icon.stat().st_size} bytes)")
    
    print("-" * 60)
    print()
    return True

def build():
    """Build the application using PyInstaller."""
    
    if not check_environment():
        sys.exit(1)
    
    print("⚙️  Running PyInstaller...")
    print("=" * 60)
    
    # Clean previous builds
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    
    # PyInstaller command with all hidden imports
    cmd = [
        "pyinstaller",
        str(GUI_SCRIPT),
        "--name", "JobApplicationBot",
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        # Hidden imports for all modules
        "--hidden-import", "database",
        "--hidden-import", "main",
        "--hidden-import", "tailor",
        "--hidden-import", "matcher",
        "--hidden-import", "config.settings",
        "--hidden-import", "config.prompt_manager",
        "--hidden-import", "sqlalchemy",
        "--hidden-import", "sqlalchemy.ext.declarative",
        "--hidden-import", "jinja2",
        "--hidden-import", "PIL",
        "--hidden-import", "tkinter",
        # Data files
        "--add-data", f"{ROOT_DIR}/config:config",
        "--add-data", f"{ROOT_DIR}/prompts:prompts",
        "--add-data", f"{ROOT_DIR}/assets:assets",
        # Splash screen
        "--splash", f"{ROOT_DIR}/assets/splash.png",
    ]
    
    # Add macOS icon if available
    macos_icon = ROOT_DIR / "assets" / "icon.icns"
    if macos_icon.exists():
        cmd.extend(["--icon", str(macos_icon)])
    
    print(f"   Running: {' '.join(cmd)}")
    print()
    
    # Run PyInstaller
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    
    if result.returncode != 0:
        print("❌ Build failed!")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✅ Build completed successfully!")
    print("=" * 60)
    print()
    print("📦 Distribution Instructions")
    print("=" * 60)
    print("✅ The executable is located in the './dist' folder.")
    print("⚠️  CRITICAL: Users must place their own '.env' file containing API keys")
    print("⚠️            in the same directory as the executable.")
    print("✅ App bundle: ./dist/JobApplicationBot.app")
    print()
    print("📋 NEXT STEPS & VERIFICATION")
    print("=" * 60)
    print("⚠️  1. CRITICAL: Provide the .env file with your API keys next to the executable.")
    print("2. Launch the application from the 'dist' folder to verify functionality.")
    print("3. Check for the customized icon on the application file/bundle.")
    print()

if __name__ == "__main__":
    build()

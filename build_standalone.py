#!/usr/bin/env python3
"""
Build script for JobApplicationBot - Creates standalone executable with PyInstaller
"""

import platform
import subprocess
import sys
from pathlib import Path

def build_executable():
    ROOT_DIR = Path(__file__).parent.resolve()
    MAIN_SCRIPT = ROOT_DIR / "gui" / "tkinter_app.py"
    
    # Base PyInstaller command (cross-platform compatible)
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        str(MAIN_SCRIPT),
        "--name", "JobApplicationBot",
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--paths", str(ROOT_DIR),
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
        "--add-data", f"{ROOT_DIR / 'config'}:config",
        "--add-data", f"{ROOT_DIR / 'prompts'}:prompts",
        "--add-data", f"{ROOT_DIR / 'assets'}:assets",
        "--add-data", f"{ROOT_DIR / 'database'}:database",
        "--icon", str(ROOT_DIR / "assets" / "icon.icns"),
    ]
    
    # Add splash screen only on non-macOS platforms
    if platform.system() != "Darwin":
        splash_path = ROOT_DIR / "assets" / "splash.png"
        if splash_path.exists():
            pyinstaller_cmd.extend(["--splash", str(splash_path)])
        else:
            print(f"  Splash screen not found at {splash_path}")
    
    print(f" Verifying build environment...")
    print("=" * 60)
    
    # Verify Python version
    print(f" Python {sys.version.split()[0]}")
    
    # Verify PyInstaller
    try:
        import PyInstaller
        print(f" PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print(" PyInstaller not found. Install with: pip install pyinstaller")
        return False
    
    # Verify Pillow
    try:
        import PIL
        print(f" Pillow (for icon conversion)")
    except ImportError:
        print(" Pillow not found. Install with: pip install Pillow")
        return False
    
    # Verify main script
    if MAIN_SCRIPT.exists():
        print(f" Main GUI script found: {MAIN_SCRIPT}")
    else:
        print(f" Main script not found: {MAIN_SCRIPT}")
        return False
    
    # Verify .env file
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        print(f" .env configuration file found (Will NOT be bundled)")
        print("   (This is correct - users must provide their own API keys)")
    else:
        print(f"  Warning: .env file not found at {env_file}")
        print("   (Users will need to create this themselves)")
    
    # Verify icon files
    icon_dir = ROOT_DIR / "assets"
    if (icon_dir / "icon.ico").exists():
        print(f"    - Windows icon: {icon_dir / 'icon.ico'} ({(icon_dir / 'icon.ico').stat().st_size:,} bytes)")
    if (icon_dir / "icon.icns").exists():
        print(f"    - macOS icon: {icon_dir / 'icon.icns'} {(icon_dir / 'icon.icns').stat().st_size:,} bytes)")
    
    print("-" * 60)
    
    # Run PyInstaller
    print(f"\n  Running PyInstaller...")
    print("=" * 60)
    print(f"   Running: {' '.join(pyinstaller_cmd)}\n")
    
    try:
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=False)
        print("\n" + "=" * 60)
        print(" Build completed successfully!")
        print("=" * 60)
        
        print("\n Distribution Instructions")
        print("=" * 60)
        print(" The executable is located in the './dist' folder.")
        print("  CRITICAL: Users must place their own '.env' file containing API keys")
        print("            in the same directory as the executable.")
        print(f" App bundle: ./dist/JobApplicationBot.app")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n Build failed!")
        print(f"Error code: {e.returncode}")
        return False
    except KeyboardInterrupt:
        print("\n\n  Build interrupted by user")
        return False
    except Exception as e:
        print(f"\n Build failed with unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)

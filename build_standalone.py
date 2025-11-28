#!/usr/bin/env python3
"""
Job Application Bot - Standalone Build Script
Creates distributable executables for Windows, macOS, and Linux
"""

import os
import sys
import argparse
import platform
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional

# Build dependencies - install these before running:
# pip install pyinstaller Pillow
try:
    import PyInstaller
    from PIL import Image
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install required packages: pip install pyinstaller Pillow")
    sys.exit(1)


class BuildError(Exception):
    """Custom exception for build errors"""
    pass


class Colors:
    """ANSI color codes for terminal output"""
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{title}{Colors.END}")
    print("=" * 60)


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_warning(message: str):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def check_environment() -> dict:
    """
    Verify build environment and return status dict
    """
    print_section("🔍 Verifying build environment...")
    
    status = {
        'python': False,
        'pyinstaller': False,
        'pillow': False,
        'gui_script': False,
        'env_file': False,
        'errors': []
    }
    
    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_success(f"Python {python_version}")
    status['python'] = True
    
    # Check PyInstaller
    try:
        version = PyInstaller.__version__
        print_success(f"PyInstaller {version}")
        status['pyinstaller'] = True
    except Exception as e:
        print_error(f"PyInstaller not found: {e}")
        status['errors'].append("PyInstaller missing")
    
    # Check Pillow
    try:
        from PIL import Image, ImageDraw
        print_success("Pillow (for icon conversion)")
        status['pillow'] = True
    except ImportError:
        print_error("Pillow not found")
        status['errors'].append("Pillow missing")
    
    # Check GUI script
    gui_script = Path("gui/tkinter_app.py")
    if gui_script.exists():
        print_success(f"Main GUI script found: {gui_script}")
        status['gui_script'] = True
    else:
        print_error(f"GUI script not found: {gui_script}")
        status['errors'].append("GUI script missing")
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        # NOTE: We do not bundle this file for security, but we verify its existence for a functional test
        print_success(".env configuration file found (Will NOT be bundled)")
        status['env_file'] = True
    else:
        print_warning(".env file not found - app won't run without user providing one.")
    
    # Check icons
    check_icons()
    
    return status


def check_icons():
    """Check for icon files"""
    icon_png = Path("assets/icon.png")
    icon_ico = Path("assets/icon.ico")
    icon_icns = Path("assets/icon.icns")
    
    print("   Icon Files:")
    if icon_png.exists():
        size = icon_png.stat().st_size
        print_success(f"   - Source icon: {icon_png} ({size} bytes)")
    
    if icon_ico.exists():
        size = icon_ico.stat().st_size
        print_success(f"   - Windows icon: {icon_ico} ({size} bytes)")
    
    if icon_icns.exists():
        size = icon_icns.stat().st_size
        print_success(f"   - macOS icon: {icon_icns} ({size} bytes)")
    print("-" * 60)


def find_best_icon_for_platform() -> tuple:
    """
    Find the best icon for current platform, converting PNG if necessary.
    Returns: (icon_path, is_converted)
    """
    print_section("🔍 Searching for best icon...")
    
    icon_png = Path("assets/icon.png")
    icon_ico = Path("assets/icon.ico")
    icon_icns = Path("assets/icon.icns")
    
    system = platform.system()
    
    if system == "Darwin":
        # macOS: Prioritize .icns, then convert PNG
        if icon_icns.exists():
            print_success(f"Found existing macOS icon: {icon_icns}")
            return str(icon_icns), False
        elif icon_png.exists():
            print_success(f"Found source icon: {icon_png}")
            print("🔄 Converting PNG to ICNS format...")
            icns_path = convert_png_to_icns(icon_png)
            print_success(f"Created macOS icon: {icns_path}")
            return str(icns_path), True
        else:
            raise BuildError("No suitable icon found (assets/icon.png or assets/icon.icns missing)")
    
    elif system == "Windows":
        # Windows: Use .ico if available
        if icon_ico.exists():
            print_success(f"Found Windows icon: {icon_ico}")
            return str(icon_ico), False
        elif icon_png.exists():
            # PyInstaller can usually use PNG directly on Windows, but ICO is standard
            print_warning("Using PNG for Windows (ICO preferred: assets/icon.ico)")
            return str(icon_png), False
        else:
            raise BuildError("No suitable icon found (assets/icon.png or assets/icon.ico missing)")
    
    else:  # Linux
        # Linux: Use PNG
        if icon_png.exists():
            print_success(f"Found Linux icon: {icon_png}")
            return str(icon_png), False
        else:
            raise BuildError("No suitable icon found (assets/icon.png missing)")


def convert_png_to_icns(png_path: Path) -> Path:
    """
    Convert PNG to ICNS format for macOS.
    Requires 'iconutil' to be available on the system.
    """
    icns_path = png_path.parent / "icon.icns"
    
    # Create iconset directory structure
    iconset_dir = png_path.parent / "icon.iconset"
    
    if icns_path.exists():
        icns_path.unlink()
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
        
    iconset_dir.mkdir(exist_ok=True)
    
    try:
        # Create different sizes using PIL
        from PIL import Image
        
        # Standard sizes for ICNS file (name: size)
        sizes = {
            'icon_16x16.png': 16, 
            'icon_16x16@2x.png': 32, 
            'icon_32x32.png': 32, 
            'icon_32x32@2x.png': 64,
            'icon_128x128.png': 128, 
            'icon_128x128@2x.png': 256, 
            'icon_256x256.png': 256, 
            'icon_256x256@2x.png': 512,
            'icon_512x512.png': 512, 
            'icon_512x512@2x.png': 1024,
        }
        
        with Image.open(png_path) as img:
            for filename, size in sizes.items():
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(iconset_dir / filename)
        
        # Convert iconset to icns using the system tool
        subprocess.run([
            'iconutil', '-c', 'icns', str(iconset_dir)
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Clean up iconset directory
        shutil.rmtree(iconset_dir)
        
        return icns_path
        
    except FileNotFoundError:
        raise BuildError("The 'iconutil' tool is required for macOS icon conversion but was not found.")
    except subprocess.CalledProcessError as e:
        print_error(f"iconutil error: {e.stderr.decode().strip()}")
        raise BuildError(f"Failed to convert PNG to ICNS. Is the PNG valid?")
    except Exception as e:
        raise BuildError(f"Failed to convert PNG to ICNS: {e}")


def get_platform_options() -> List[str]:
    """
    Get PyInstaller platform-specific options
    """
    system = platform.system()
    options = []
    
    if system == "Darwin":
        # macOS bundle options
        options.extend([
            '--windowed',  # Use windowed mode (no console)
            '--osx-bundle-identifier', 'com.micouwr.jobapplicationbot',
        ])
    
    elif system == "Windows":
        # Windows-specific options
        options.extend([
            '--windowed',
            '--version-file', 'config/version.txt', # Ensure this file exists
        ])
    
    else:  # Linux
        options.extend([
            '--windowed',
        ])
    
    return options


def clean_build_artifacts():
    """
    Clean previous build artifacts
    """
    print_section("🧹 Cleaning previous build artifacts...")
    
    dirs_to_clean = ['build', 'dist']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print_success(f"Removed {dir_name}/ directory")
    
    for pattern in files_to_clean:
        for file in Path('.').glob(pattern):
            file.unlink()
            print_success(f"Removed {file}")


def build_executable(clean: bool = False):
    """
    Build the standalone executable
    """
    if clean:
        clean_build_artifacts()
    
    # Verify environment
    status = check_environment()
    
    if status.get('errors'):
        print_error("Cannot build due to missing dependencies.")
        sys.exit(1)
    
    try:
        # Find icon
        icon_path, was_converted = find_best_icon_for_platform()
    except BuildError as e:
        print_error(f"Icon Error: {e}")
        sys.exit(1)
    
    print_section("⚙️  Running PyInstaller...")
    
    # --- PyInstaller Configuration ---

    # Critical imports that need to be explicitly included
    hidden_imports = [
        # Database and ORM
        'sqlalchemy.ext.declarative',
        # AI/NLP dependencies
        'google.genai',
        'tiktoken', 
        # GUI
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox',
        # Templating (for cover letters)
        'jinja2',
        # Sub-modules of the main package (critical for one-dir build)
        'config.settings',
    ]
    
    # Data files to bundle (Source_path:destination_in_bundle)
    # NOTE: DO NOT INCLUDE .env for security reasons.
    datas = [
        'config:config', # Include the config directory (for version.txt, etc.)
        'assets:assets', # Include all assets (icons, etc.)
    ]
    
    # We explicitly collect data for known trouble-makers like tiktoken
    collect_data = [
        'tiktoken', 
        'tiktoken_ext',
        'sqlalchemy',
    ]
    
    # Base PyInstaller command
    cmd = [
        'pyinstaller',
        # Main script to execute on launch
        'gui/tkinter_app.py',
        '--name', 'JobApplicationBot',
        '--onedir', # Create a single directory containing the executable and dependencies
        '--noconfirm',
        '--clean',
        '--icon', icon_path,
        # Remove hardcoded path: PyInstaller figures out --paths if run from root
        
        # Collect data
        *[f'--collect-data={d}' for d in collect_data],
    ]
    
    # Add hidden imports
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    # Add data files
    for data in datas:
        cmd.extend(['--add-data', data])
    
    # Add platform-specific options
    cmd.extend(get_platform_options())
    
    # Set output paths
    cmd.extend([
        '--distpath', './dist',
        '--workpath', './build',
    ])
    
    # --- Execution ---

    print(f"   Running: pyinstaller gui/tkinter_app.py --name JobApplicationBot --onedir ...")
    
    try:
        # Execute the command
        subprocess.run(cmd, check=True)
        print_section("✅ Build completed successfully!")
        
        # Post-build instructions
        print_section("📦 Distribution Instructions")
        print_success("The executable is located in the './dist' folder.")
        print_warning("CRITICAL: Users must place their own '.env' file containing API keys")
        print_warning("          in the same directory as the executable.")
        
        if platform.system() == "Darwin":
            print_success("App bundle: ./dist/JobApplicationBot.app")
        elif platform.system() == "Windows":
            print_success("Executable: ./dist/JobApplicationBot/JobApplicationBot.exe")
        else:
            print_success("Executable: ./dist/JobApplicationBot/JobApplicationBot")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"PyInstaller failed with return code {e.returncode}")
        print_error("Check the full log in the 'build' folder for details.")
        return False
    except Exception as e:
        print_error(f"An unexpected error occurred during build: {e}")
        return False


def create_desktop_integration():
    """
    Create desktop shortcuts and integration
    """
    print_section("🔗 Creating Desktop Integration...")
    system = platform.system()
    
    # Check if the primary distribution directory exists
    dist_path = Path("dist/JobApplicationBot")
    if not dist_path.exists():
        print_warning("Skipping integration: Distribution directory not found.")
        return

    if system == "Darwin":
        # Copy to Applications folder (requires admin, often fails without user permission)
        try:
            app_path = Path("dist/JobApplicationBot.app")
            if app_path.exists():
                # We won't attempt the copy as it requires permissions, just inform the user
                print_warning("macOS: Please drag 'dist/JobApplicationBot.app' to your Applications folder manually.")
                return 
        except Exception:
             print_warning("macOS: Could not locate .app bundle.")
             
    elif system == "Windows":
        # Create desktop shortcut (requires winshell/pywin32)
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = Path(desktop) / "JobApplicationBot.lnk"
            target = (dist_path / "JobApplicationBot.exe").resolve()
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(target)
            shortcut.IconLocation = str(target)
            shortcut.WorkingDirectory = str(target.parent)
            shortcut.save()
            
            print_success(f"Windows Desktop shortcut created: {shortcut_path}")
        except ImportError:
            print_warning("Could not create Windows shortcut (missing 'winshell' or 'pywin32').")
        except Exception as e:
            print_warning(f"Could not create Windows shortcut: {e}")
    
    else:  # Linux
        # Create .desktop entry
        try:
            desktop_entry = Path.home() / ".local/share/applications/JobApplicationBot.desktop"
            desktop_entry.parent.mkdir(parents=True, exist_ok=True)
            
            # Resolve the path to the executable inside the dist directory
            executable_path = (dist_path / "JobApplicationBot").resolve()
            icon_path = Path('assets/icon.png').resolve()
            
            content = f"""[Desktop Entry]
Name=Job Application Bot
Comment=AI-Powered Resume Tailoring Tool
Exec={executable_path}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Office;
"""
            desktop_entry.write_text(content)
            desktop_entry.chmod(0o755)
            print_success(f"Linux Desktop entry created: {desktop_entry}")
        except Exception as e:
            print_warning(f"Could not create .desktop entry: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Build Job Application Bot standalone executable")
    parser.add_argument('--clean', action='store_true', help="Clean build artifacts before building")
    parser.add_argument('--no-desktop', action='store_true', help="Skip desktop integration")
    args = parser.parse_args()
    
    success = build_executable(clean=args.clean)
    
    if success and not args.no_desktop:
        create_desktop_integration()
        
        # Post-build verification steps
        print_section("📋 NEXT STEPS & VERIFICATION")
        print_warning("1. CRITICAL: Provide the .env file with your API keys next to the executable.")
        print("2. Launch the application from the 'dist' folder to verify functionality.")
        print("3. Check for the customized icon on the application file/bundle.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
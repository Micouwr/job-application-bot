#!/usr/bin/env python3
"""
Job Application Bot - Standalone Build Script
Creates distributable executables for Windows, macOS, and Linux
"""

import os
import sys
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
        print_success(".env configuration file found")
        status['env_file'] = True
    else:
        print_warning(".env file not found - app won't run without it")
    
    # Check icons
    check_icons()
    
    return status


def check_icons():
    """Check for icon files"""
    icon_png = Path("assets/icon.png")
    icon_ico = Path("assets/icon.ico")
    icon_icns = Path("assets/icon.icns")
    
    if icon_png.exists():
        size = icon_png.stat().st_size
        print_success(f"Source icon: {icon_png} ({size} bytes)")
    
    if icon_ico.exists():
        size = icon_ico.stat().st_size
        print_success(f"Windows icon: {icon_ico} ({size} bytes)")
    
    if icon_icns.exists():
        size = icon_icns.stat().st_size
        print_success(f"macOS icon: {icon_icns} ({size} bytes)")


def find_best_icon_for_platform() -> tuple:
    """
    Find the best icon for current platform
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
            print_success(f"Found macOS icon: {icon_icns}")
            print("   (Skipping conversion - using existing .icns file)")
            return str(icon_icns), False
        elif icon_png.exists():
            print_success(f"Found source icon: {icon_png}")
            print("🔄 Converting PNG to ICNS format...")
            icns_path = convert_png_to_icns(icon_png)
            print_success(f"Created macOS icon: {icns_path}")
            return icns_path, True
        else:
            raise BuildError("No suitable icon found for macOS")
    
    elif system == "Windows":
        # Windows: Use .ico if available
        if icon_ico.exists():
            print_success(f"Found Windows icon: {icon_ico}")
            return str(icon_ico), False
        elif icon_png.exists():
            print_warning("Using PNG for Windows (ICO preferred)")
            return str(icon_png), False
        else:
            raise BuildError("No suitable icon found for Windows")
    
    else:  # Linux
        # Linux: Use PNG
        if icon_png.exists():
            print_success(f"Found Linux icon: {icon_png}")
            return str(icon_png), False
        else:
            raise BuildError("No suitable icon found for Linux")


def convert_png_to_icns(png_path: Path) -> Path:
    """
    Convert PNG to ICNS format for macOS
    Uses iconutil (macOS built-in tool)
    """
    icns_path = png_path.parent / "icon.icns"
    
    # Create iconset directory structure
    iconset_dir = png_path.parent / "icon.iconset"
    iconset_dir.mkdir(exist_ok=True)
    
    try:
        # Create different sizes using PIL
        from PIL import Image
        
        sizes = [16, 32, 128, 256, 512, 1024]
        
        with Image.open(png_path) as img:
            for size in sizes:
                # Create @1x version
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(iconset_dir / f"icon_{size}x{size}.png")
                
                # Create @2x version for retina
                if size <= 512:
                    resized2x = img.resize((size*2, size*2), Image.Resampling.LANCZOS)
                    resized2x.save(iconset_dir / f"icon_{size}x{size}@2x.png")
        
        # Convert iconset to icns
        subprocess.run([
            'iconutil', '-c', 'icns', str(iconset_dir)
        ], check=True)
        
        # Clean up iconset directory
        shutil.rmtree(iconset_dir)
        
        return icns_path
        
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
        # REMOVED: --target-architecture universal2 (causes fat binary errors)
    
    elif system == "Windows":
        # Windows-specific options
        options.extend([
            '--windowed',
            '--version-file', 'config/version.txt',
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
        print_error("Cannot build due to missing dependencies:")
        for error in status['errors']:
            print_error(f"  - {error}")
        sys.exit(1)
    
    # Find icon
    icon_path, was_converted = find_best_icon_for_platform()
    
    if was_converted and platform.system() == "Darwin":
        print_success(f"Generated macOS icon: {icon_path}")
    
    print_section("⚙️  Running PyInstaller...")
    
    # Hidden imports for PyInstaller to bundle
    # ✅ CRITICAL FIX: Added ALL project modules
    hidden_imports = [
        'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.ext.declarative',
        'google.genai', 'google.genai.types',
        'tiktoken', 'tiktoken_ext',
        'PyPDF2', 'PIL', 'PIL.Image',
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox',
        
        # ✅ PROJECT MODULES - Must be included!
        'database',
        'tailor',
        'matcher',
        'scraper',
        'config.settings',
    ]
    
    # Data files to bundle (config, assets, etc.)
    # ✅ CRITICAL FIX: Added project root modules
    datas = [
        'config:config',
        'assets:assets',
        '.env:.',
        'database.py:.',
        'tailor.py:.',
        'matcher.py:.',
        'scraper.py:.',
        'main.py:.',
    ]
    
    # Base PyInstaller command
    cmd = [
        'pyinstaller',
        'gui/tkinter_app.py',
        '--name', 'JobApplicationBot',
        '--onedir',  # ✅ CHANGED FROM --onefile
        '--noconfirm',
        '--clean',
        '--icon', icon_path,
        '--paths', '/Users/chellenicole/Desktop/job-application-bot',  # ✅ CRITICAL: Add project root
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
    
    print(f"   Command: pyinstaller gui/tkinter_app.py --name JobApplicationBot --onedir --windowed --noconfirm --clean --icon {icon_path} ...")
    
    # Run PyInstaller
    try:
        subprocess.run(cmd, check=True)
        print_section("✅ Build completed successfully!")
        
        if platform.system() == "Darwin":
            print_success("App bundle: ./dist/JobApplicationBot.app")
            print_success("Executable: ./dist/JobApplicationBot/JobApplicationBot")
        else:
            print_success("Executable location: ./dist/JobApplicationBot")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"Build failed with return code {e.returncode}")
        return False


def create_desktop_integration():
    """
    Create desktop shortcuts and integration
    """
    system = platform.system()
    
    if system == "Darwin":
        # Copy to Applications folder (requires admin)
        try:
            app_path = Path("dist/JobApplicationBot.app")
            if app_path.exists():
                apps_path = Path("/Applications/JobApplicationBot.app")
                subprocess.run([
                    'cp', '-R', str(app_path), str(apps_path)
                ], check=True)
                print_success("Copied to Applications folder")
        except Exception:
            print_warning("Could not copy to Applications (try manually)")
    
    elif system == "Windows":
        # Create desktop shortcut
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = Path(desktop) / "JobApplicationBot.lnk"
            target = Path("dist/JobApplicationBot/JobApplicationBot").resolve()
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(target)
            shortcut.IconLocation = str(target)
            shortcut.WorkingDirectory = str(target.parent)
            shortcut.save()
            
            print_success(f"Desktop shortcut created: {shortcut_path}")
        except Exception:
            print_warning("Could not create desktop shortcut")
    
    else:  # Linux
        # Create .desktop entry
        try:
            desktop_entry = Path.home() / ".local/share/applications/JobApplicationBot.desktop"
            desktop_entry.parent.mkdir(parents=True, exist_ok=True)
            
            content = f"""[Desktop Entry]
Name=Job Application Bot
Comment=AI-Powered Resume Tailoring Tool
Exec={Path('dist/JobApplicationBot').resolve()}
Icon={Path('assets/icon.png').resolve()}
Terminal=false
Type=Application
Categories=Office;
"""
            desktop_entry.write_text(content)
            desktop_entry.chmod(0o755)
            print_success(f"Desktop entry created: {desktop_entry}")
        except Exception:
            print_warning("Could not create .desktop entry")


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
        print_section("📋 POST-BUILD VERIFICATION")
        print("\n1. 📁 Verify executable exists:")
        print("   ls -lh dist/JobApplicationBot/JobApplicationBot")
        print("\n2. ✅ Check custom icon is embedded:")
        print("   Right-click .app → Get Info should show custom icon")
        print("\n3. 🚀 First run test:")
        print("   ./dist/JobApplicationBot/JobApplicationBot")
        print("\n4. 📄 Upload your new resume:")
        print("   - Launch application")
        print("   - Go to 📄 Manage Resumes tab")
        print("   - Click ⬆️ Upload New Resume")
        print("   - Select your updated resume")
        print("   - Click ✅ Set as Active")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

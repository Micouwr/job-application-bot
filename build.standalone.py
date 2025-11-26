#!/usr/bin/env python3
"""
build_standalone.py - Production build script for Job Application Bot GUI

Creates standalone executable with:
- Single-file bundling (onefile)
- Native OS integration (windowed, icons)
- Desktop shortcuts
- Cross-platform support (Windows, macOS, Linux)
- Hidden imports for complex packages
- Resource file bundling (.env, configs, data dirs)
- Automatic icon conversion from assets/icon.png

USAGE:
    python build_standalone.py
    python build_standalone.py --clean  # Force clean build
    python build_standalone.py --no-shortcut  # Skip desktop shortcuts
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

def clean_build_artifacts():
    """Removes previous build artifacts."""
    print("🧹 Cleaning previous build artifacts...")
    for artifact in ['build', 'dist', '__pycache__']:
        if Path(artifact).exists():
            shutil.rmtree(artifact)
            print(f"   Removed ./{artifact}/")
    
    # Remove .spec files
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"   Removed {spec_file.name}")

def convert_icon_if_needed() -> Optional[Path]:
    """
    Checks for assets/icon.png and converts to platform-specific format.
    Returns path to converted icon or None if conversion fails.
    """
    assets_dir = Path("assets")
    source_icon = assets_dir / "icon.png"
    
    # Check if source icon exists
    if not source_icon.exists():
        print(f"⚠️  Source icon not found: {source_icon}")
        print("   For best results, place a 256x256 PNG in ./assets/icon.png")
        return None
    
    print(f"✅ Found source icon: {source_icon}")
    
    # Platform-specific icon formats
    is_windows = sys.platform.startswith('win')
    is_macos = sys.platform == 'darwin'
    
    if is_windows:
        target_icon = assets_dir / "icon.ico"
        if convert_png_to_ico(source_icon, target_icon):
            return target_icon
    elif is_macos:
        target_icon = assets_dir / "icon.icns"
        if convert_png_to_icns(source_icon, target_icon):
            return target_icon
    else:
        # Linux can use PNG directly
        print(f"✅ Using PNG icon for Linux: {source_icon}")
        return source_icon
    
    return None

def convert_png_to_ico(source: Path, target: Path) -> bool:
    """
    Converts PNG to ICO format using Pillow.
    Returns True if successful.
    """
    try:
        from PIL import Image
        
        print("🔄 Converting PNG to ICO format...")
        img = Image.open(source)
        
        # Create multiple sizes for ICO
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        icons = []
        
        for size in sizes:
            icon = img.resize(size, Image.Resampling.LANCZOS)
            icons.append(icon)
        
        # Save as ICO
        icons[0].save(target, format='ICO', append_images=icons[1:], sizes=[(s[0], s[1]) for s in sizes])
        
        print(f"✅ Created Windows icon: {target}")
        return True
        
    except ImportError:
        print("   ⚠️  Pillow not installed. Install: pip install Pillow")
        print(f"   You can manually convert {source} to .ico online")
        return False
    except Exception as e:
        print(f"   ❌ Failed to convert PNG to ICO: {e}")
        print(f"   You can manually convert {source} to .ico online")
        return False

def convert_png_to_icns(source: Path, target: Path) -> bool:
    """
    Converts PNG to ICNS format using iconutil (macOS native).
    Returns True if successful.
    """
    try:
        if sys.platform != 'darwin':
            print("   ⚠️  ICNS conversion requires macOS")
            return False
        
        print("🔄 Converting PNG to ICNS format...")
        
        # Create iconset directory
        iconset_dir = source.parent / "icon.iconset"
        iconset_dir.mkdir(exist_ok=True)
        
        # Generate different sizes
        from PIL import Image
        img = Image.open(source)
        
        sizes = {
            'icon_16x16.png': (16, 16),
            'icon_32x32.png': (32, 32),
            'icon_128x128.png': (128, 128),
            'icon_256x256.png': (256, 256),
            'icon_512x512.png': (512, 512),
        }
        
        for filename, size in sizes.items():
            resized = img.resize(size, Image.Resampling.LANCZOS)
            resized.save(iconset_dir / filename)
            
            # Add @2x versions
            if size[0] <= 256:  # Max 512x512 for @2x
                resized_2x = img.resize((size[0]*2, size[1]*2), Image.Resampling.LANCZOS)
                resized_2x.save(iconset_dir / filename.replace('.png', '@2x.png'))
        
        # Convert to ICNS
        subprocess.run(['iconutil', '-c', 'icns', str(iconset_dir)], check=True)
        
        print(f"✅ Created macOS icon: {target}")
        
        # Cleanup
        shutil.rmtree(iconset_dir)
        
        return True
        
    except ImportError:
        print("   ⚠️  Pillow not installed. Install: pip install Pillow")
        print(f"   You can manually convert {source} to .icns")
        return False
    except subprocess.CalledProcessError:
        print("   ⚠️  iconutil failed. Install Xcode Command Line Tools")
        return False
    except Exception as e:
        print(f"   ❌ Failed to convert PNG to ICNS: {e}")
        print(f"   You can manually convert {source} to .icns online")
        return False

def check_and_prepare_icon() -> Optional[Path]:
    """
    Main function to check and prepare icon for build.
    Attempts conversion if needed.
    """
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    # Check for source PNG
    source_icon = assets_dir / "icon.png"
    if not source_icon.exists():
        print(f"⚠️  No icon.png found in {assets_dir}/")
        print("   Create a 256x256 PNG and place it in ./assets/icon.png")
        print("   Build will continue without icon")
        return None
    
    # Platform-specific icon handling
    is_windows = sys.platform.startswith('win')
    is_macos = sys.platform == 'darwin'
    
    if is_windows:
        icon_path = assets_dir / "icon.ico"
        if icon_path.exists():
            print(f"✅ Windows icon exists: {icon_path}")
            return icon_path
        else:
            return convert_png_to_ico(source_icon, icon_path)
    
    elif is_macos:
        icon_path = assets_dir / "icon.icns"
        if icon_path.exists():
            print(f"✅ macOS icon exists: {icon_path}")
            return icon_path
        else:
            return convert_png_to_icns(source_icon, icon_path)
    
    else:  # Linux
        # Linux can use PNG directly with some desktop environments
        print(f"✅ Using PNG icon for Linux: {source_icon}")
        return source_icon

def get_pyinstaller_command(icon_path: Optional[Path], clean: bool = False) -> List[str]:
    """
    Constructs PyInstaller command with all required parameters.
    
    Args:
        icon_path: Path to icon file
        clean: Whether to force clean build
    """
    
    # Base command
    cmd = [
        'gui/tkinter_app.py',           # Main script
        '--name', 'JobApplicationBot',  # Application name
        '--onefile',                    # Single executable file
        '--windowed',                   # No console window (GUI mode)
        '--noconfirm',                  # Overwrite without prompting
    ]
    
    if clean:
        cmd.append('--clean')           # Clean cache
    
    # Icon (platform-specific)
    if icon_path:
        cmd.extend(['--icon', str(icon_path)])
        print(f"   Using icon: {icon_path}")
    else:
        print("   No icon available - build will use default PyInstaller icon")
    
    # Add data files and directories
    separator = ';' if sys.platform.startswith('win') else ':'
    
    # Core directories and files
    data_mappings = [
        ('config', 'config'),
        ('data', 'data'),
        ('logs', 'logs'),
        ('output', 'output'),
        ('assets', 'assets'),
        ('.env', '.'),  # Must be in root for config loader
    ]
    
    for src, dest in data_mappings:
        if Path(src).exists():
            cmd.extend(['--add-data', f'{src}{separator}{dest}'])
            print(f"   Added data: {src} → {dest}")
    
    # Add individual config file
    if Path('config/settings.py').exists():
        cmd.extend(['--add-data', f'config/settings.py{separator}config'])
    
    # Hidden imports for packages PyInstaller might miss
    hidden_imports = [
        'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.ext.declarative',
        'google.genai', 'google.genai.types',
        'tiktoken', 'tiktoken_ext',
        'PyPDF2', 'PIL', 'PIL.Image',
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox',
    ]
    
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    # Output directories
    cmd.extend([
        '--distpath', './dist',
        '--workpath', './build',
    ])
    
    # macOS-specific: Create .app bundle
    if sys.platform == 'darwin':
        cmd.extend([
            '--osx-bundle-identifier', 'com.micouwr.jobapplicationbot',
            '--target-architecture', 'universal2',
        ])
    
    # Windows-specific: Version info
    if sys.platform.startswith('win'):
        version_file = create_windows_version_file()
        if version_file:
            cmd.extend(['--version-file', str(version_file)])
    
    return cmd

def create_windows_version_file() -> Optional[Path]:
    """
    Creates a version resource file for Windows executables.
    Makes the .exe look professional in file properties.
    """
    try:
        version_content = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers=(2, 0, 0, 0), prodvers=(2, 0, 0, 0), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([
      StringTable(u'040904B0', [
        StringStruct(u'CompanyName', u'Ryan Micou'),
        StringStruct(u'FileDescription', u'Job Application Bot'),
        StringStruct(u'FileVersion', u'2.0.0.0'),
        StringStruct(u'InternalName', u'JobApplicationBot'),
        StringStruct(u'LegalCopyright', u'© 2025 Ryan Micou'),
        StringStruct(u'OriginalFilename', u'JobApplicationBot.exe'),
        StringStruct(u'ProductName', u'Job Application Bot'),
        StringStruct(u'ProductVersion', u'2.0.0.0')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
        
        version_file = Path('version.txt')
        version_file.write_text(version_content, encoding='utf-8')
        print("✅ Created Windows version resource file")
        return version_file
        
    except Exception as e:
        print(f"⚠️  Could not create version file: {e}")
        return None

def create_windows_shortcut():
    """Creates a desktop shortcut for Windows executable."""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = Path(winshell.desktop())
        shortcut_path = desktop / "Job Application Bot.lnk"
        target = Path("dist/JobApplicationBot.exe").absolute()
        
        if not target.exists():
            print(f"⚠️  Cannot create shortcut: {target} not found")
            return
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(Path.cwd())
        shortcut.IconLocation = str(target)
        shortcut.save()
        
        print(f"🎯 Desktop shortcut created: {shortcut_path}")
        print(f"   You can now launch from your desktop!")
        
    except ImportError:
        print("💡 Install winshell for auto-shortcut: pip install winshell pywin32")
        print("   Manual shortcut: Right-click .exe → Send to → Desktop")
    except Exception as e:
        print(f"⚠️  Could not create shortcut: {e}")

def create_linux_desktop_entry():
    """Creates a .desktop file for Linux systems."""
    try:
        applications_dir = Path.home() / ".local/share/applications"
        applications_dir.mkdir(exist_ok=True)
        
        desktop_file = applications_dir / "JobApplicationBot.desktop"
        
        # Use PNG icon directly
        icon_path = Path("assets/icon.png").absolute()
        exec_path = Path("dist/JobApplicationBot").absolute()
        
        # Make executable
        if exec_path.exists():
            exec_path.chmod(0o755)
        
        content = f"""[Desktop Entry]
Name=Job Application Bot
Comment=AI-Powered Resume Tailorer
Exec={exec_path}
Icon={icon_path}
Terminal=false
Type=Application
Categories=Office;Utility;
StartupNotify=true
Keywords=job;resume;ai;career;
X-Desktop-File-Install-Version=0.26
"""
        
        desktop_file.write_text(content)
        desktop_file.chmod(0o755)
        
        print(f"🎯 Linux desktop entry created: {desktop_file}")
        print(f"   You may need to log out/in to see it in applications menu")
        print(f"   Or run: update-desktop-database ~/.local/share/applications")
        
    except Exception as e:
        print(f"⚠️  Could not create desktop entry: {e}")

def post_build_instructions():
    """Prints post-build instructions."""
    print("\n" + "=" * 60)
    print("📋 POST-BUILD INSTRUCTIONS")
    print("=" * 60)
    
    exe_name = "JobApplicationBot.exe" if sys.platform.startswith('win') else "JobApplicationBot"
    exe_path = Path("dist") / exe_name
    
    print(f"\n1. Test the executable:")
    print(f"   {exe_path}")
    
    print(f"\n2. If .env wasn't bundled, copy it manually:")
    print(f"   cp .env dist/")
    
    print(f"\n3. First run checklist:")
    print(f"   - Launch the application")
    print(f"   - Go to 📄 Manage Resumes tab")
    print(f"   - Upload your new resume")
    print(f"   - Set it as active")
    print(f"   - Test tailoring with a job description")
    
    if sys.platform.startswith('win'):
        print(f"\n4. Windows: Desktop shortcut should be created automatically")
    elif sys.platform == 'darwin':
        print(f"\n4. macOS: Drag dist/JobApplicationBot.app to Applications folder")
        print(f"   Then drag to Dock for easy access")
    else:
        print(f"\n4. Linux: Desktop entry created in ~/.local/share/applications/")
        print(f"   Run 'update-desktop-database ~/.local/share/applications' to refresh")
    
    print("\n5. For distribution:")
    print(f"   - Zip the 'dist' folder")
    print(f"   - Include README.md and license")
    print(f"   - Create installer with NSIS (Windows) or create-dmg (macOS)")
    
    print("\n🎉 Build complete! Your application is ready to demo!")

def verify_environment():
    """Verifies build environment is ready."""
    print("🔍 Verifying build environment...")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Install: pip install pyinstaller")
        sys.exit(1)
    
    # Check Pillow for icon conversion
    try:
        import PIL.Image
        print(f"✅ Pillow (for icon conversion)")
    except ImportError:
        print("⚠️  Pillow not installed. Install: pip install Pillow")
        print("   Build will continue but icon conversion may fail")
    
    # Check main script
    if not Path('gui/tkinter_app.py').exists():
        print("❌ gui/tkinter_app.py not found")
        sys.exit(1)
    print("✅ Main script found")
    
    # Check assets folder
    assets_dir = Path('assets')
    if not assets_dir.exists():
        print("⚠️  assets/ folder not found. Creating...")
        assets_dir.mkdir(exist_ok=True)
    
    # Check source icon
    icon_path = assets_dir / "icon.png"
    if not icon_path.exists():
        print("⚠️  assets/icon.png not found. Build will use default PyInstaller icon")
        print("   Create a 256x256 PNG and save as assets/icon.png")
    else:
        print(f"✅ Source icon found: {icon_path}")
    
    # Check .env
    if not Path('.env').exists():
        print("⚠️  .env file not found. Build will succeed but app won't run without it")
    else:
        print("✅ .env file found")
    
    print()

def main():
    """Main build orchestration."""
    parser = argparse.ArgumentParser(
        description='Build Job Application Bot standalone executable',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_standalone.py              # Standard build
  python build_standalone.py --clean      # Force clean build
  python build_standalone.py --no-shortcut # Skip desktop integration
        """
    )
    parser.add_argument('--clean', action='store_true', help='Force clean build')
    parser.add_argument('--no-shortcut', action='store_true', help='Skip desktop shortcut creation')
    args = parser.parse_args()
    
    print("🏗️  Building Job Application Bot Standalone Executable")
    print("=" * 60)
    
    # Pre-build checks
    verify_environment()
    
    # Clean if requested
    if args.clean:
        clean_build_artifacts()
    
    # Prepare icon (convert if needed)
    icon_path = check_and_prepare_icon()
    
    # Get PyInstaller command
    pyinstaller_cmd = get_pyinstaller_command(icon_path, clean=args.clean)
    
    print("\n⚙️  Running PyInstaller...")
    print(f"   Command: pyinstaller {' '.join(pyinstaller_cmd)}")
    
    try:
        # Import and run PyInstaller programmatically
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_cmd)
        
        print("\n✅ Build completed successfully!")
        exe_name = "JobApplicationBot.exe" if sys.platform.startswith('win') else "JobApplicationBot"
        print(f"📁 Executable location: ./dist/{exe_name}")
        
        # Create shortcuts/desktop entries
        if not args.no_shortcut:
            print("\n🎯 Creating desktop integration...")
            if sys.platform.startswith('win'):
                create_windows_shortcut()
            elif sys.platform == 'darwin':
                print("   macOS: Drag .app from ./dist/ to Applications folder")
            elif sys.platform.startswith('linux'):
                create_linux_desktop_entry()
        
        # Post-build instructions
        post_build_instructions()
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

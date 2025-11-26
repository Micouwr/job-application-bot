#!/usr/bin/env python3
"""
build_standalone.py - Production build script for Job Application Bot GUI

Features:
- Smart icon detection (uses existing .ico/icns, falls back to .png)
- Automatic conversion via Pillow (macOS/Linux)
- Cross-platform support with native icon formats
- Desktop shortcuts and .desktop entries
- Full resource bundling (.env, configs, data dirs)
- Version metadata for Windows
- Post-build instructions

USAGE:
    python3 build_standalone.py --clean
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

def find_best_icon_for_platform() -> Optional[Path]:
    """
    Finds the best icon for the current platform:
    1. Checks for existing platform-specific icon (.ico/.icns)
    2. Falls back to source icon.png
    3. Attempts conversion if needed
    Returns Path to icon file or None.
    """
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    is_windows = sys.platform.startswith('win')
    is_macos = sys.platform == 'darwin'
    
    print(f"🔍 Searching for best icon for {sys.platform}...")
    
    # WINDOWS: Prioritize existing icon.ico
    if is_windows:
        ico_path = assets_dir / "icon.ico"
        if ico_path.exists():
            print(f"✅ Found Windows icon: {ico_path}")
            print("   (Skipping conversion - using existing .ico file)")
            return ico_path
    
    # macOS: Prioritize existing icon.icns
    elif is_macos:
        icns_path = assets_dir / "icon.icns"
        if icns_path.exists():
            print(f"✅ Found macOS icon: {icns_path}")
            print("   (Skipping conversion - using existing .icns file)")
            return icns_path
    
    # LINUX: Use PNG directly
    else:
        png_path = assets_dir / "icon.png"
        if png_path.exists():
            print(f"✅ Using PNG icon for Linux: {png_path}")
            return png_path
        else:
            print("   No icon.png found - build will use default PyInstaller icon")
            return None
    
    # Fallback: try conversion from PNG
    png_path = assets_dir / "icon.png"
    if png_path.exists():
        print(f"✅ Found source icon: {png_path}")
        if is_windows:
            return convert_png_to_ico(png_path, assets_dir / "icon.ico")
        elif is_macos:
            return convert_png_to_icns(png_path, assets_dir / "icon.icns")
    
    print("⚠️  No suitable icon found - build will use default PyInstaller icon")
    return None

def convert_png_to_ico(source: Path, target: Path) -> Optional[Path]:
    """
    Converts PNG to ICO format using Pillow.
    Returns Path to converted icon or None if failed.
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
        icons[0].save(target, format='ICO', append_images=icons[1:], 
                     sizes=[(s[0], s[1]) for s in sizes])
        
        print(f"✅ Created Windows icon: {target}")
        return target
        
    except ImportError:
        print("   ⚠️  Pillow not installed. Install: pip install Pillow")
        return None
    except Exception as e:
        print(f"   ❌ Failed to convert PNG to ICO: {e}")
        return None

def convert_png_to_icns(source: Path, target: Path) -> Optional[Path]:
    """
    Converts PNG to ICNS format using iconutil (macOS native).
    Returns Path to converted icon or None if failed.
    """
    try:
        if sys.platform != 'darwin':
            print("   ⚠️  ICNS conversion requires macOS")
            return None
        
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
            if size[0] <= 256:
                resized_2x = img.resize((size[0]*2, size[1]*2), Image.Resampling.LANCZOS)
                resized_2x.save(iconset_dir / filename.replace('.png', '@2x.png'))
        
        # Convert to ICNS using macOS native tool
        subprocess.run(['iconutil', '-c', 'icns', str(iconset_dir)], check=True)
        
        print(f"✅ Created macOS icon: {target}")
        
        # Cleanup
        shutil.rmtree(iconset_dir)
        
        return target
        
    except ImportError:
        print("   ⚠️  Pillow not installed. Install: pip install Pillow")
        return None
    except subprocess.CalledProcessError:
        print("   ⚠️  iconutil failed. Install Xcode Command Line Tools")
        return None
    except Exception as e:
        print(f"   ❌ Failed to convert PNG to ICNS: {e}")
        return None

def get_pyinstaller_command(icon_path: Optional[Path], clean: bool = False) -> List[str]:
    """
    Constructs PyInstaller command with all required parameters.
    """
    
    # Base command
    cmd = [
        'gui/tkinter_app.py',
        '--name', 'JobApplicationBot',
        '--onefile',
        '--windowed',
        '--noconfirm',
    ]
    
    if clean:
        cmd.append('--clean')
    
    # Add icon if available
    if icon_path:
        cmd.extend(['--icon', str(icon_path)])
        print(f"   Using icon: {icon_path}")
    else:
        print("   No icon available - using default PyInstaller icon")
    
    # Data files and directories
    separator = ';' if sys.platform.startswith('win') else ':'
    
    data_mappings = [
        ('config', 'config'),
        ('data', 'data'),
        ('logs', 'logs'),
        ('output', 'output'),
        ('assets', 'assets'),
        ('.env', '.'),
    ]
    
    for src, dest in data_mappings:
        if Path(src).exists():
            cmd.extend(['--add-data', f'{src}{separator}{dest}'])
    
    # Hidden imports
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
    
    # Platform-specific options
    if sys.platform == 'darwin':
        cmd.extend([
            '--osx-bundle-identifier', 'com.micouwr.jobapplicationbot',
            '--target-architecture', 'universal2',
        ])
    
    if sys.platform.startswith('win'):
        version_file = create_windows_version_file()
        if version_file:
            cmd.extend(['--version-file', str(version_file)])
    
    return cmd

def create_windows_version_file() -> Optional[Path]:
    """Creates version resource file for Windows."""
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
    """Creates Windows desktop shortcut."""
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
        
    except ImportError:
        print("💡 Install winshell for auto-shortcut: pip install winshell pywin32")
    except Exception as e:
        print(f"⚠️  Could not create shortcut: {e}")

def create_linux_desktop_entry():
    """Creates Linux .desktop file."""
    try:
        applications_dir = Path.home() / ".local/share/applications"
        applications_dir.mkdir(exist_ok=True)
        
        desktop_file = applications_dir / "JobApplicationBot.desktop"
        
        # Use PNG icon directly
        icon_path = Path("assets/icon.png").absolute()
        exec_path = Path("dist/JobApplicationBot").absolute()
        
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
"""
        
        desktop_file.write_text(content)
        desktop_file.chmod(0o755)
        
        print(f"🎯 Linux desktop entry created: {desktop_file}")
        
    except Exception as e:
        print(f"⚠️  Could not create desktop entry: {e}")

def post_build_instructions():
    """Prints post-build verification steps."""
    print("\n" + "=" * 60)
    print("📋 POST-BUILD VERIFICATION")
    print("=" * 60)
    
    exe_name = "JobApplicationBot.exe" if sys.platform.startswith('win') else "JobApplicationBot"
    exe_path = Path("dist") / exe_name
    
    print(f"\n1. 📁 Verify executable exists:")
    print(f"   ls -lh {exe_path}")
    print(f"\n2. ✅ Check custom icon is embedded:")
    if sys.platform.startswith('win'):
        print(f"   Right-click .exe → Properties → General tab should show icon")
    elif sys.platform == 'darwin':
        print(f"   Right-click .app → Get Info should show custom icon")
    
    print(f"\n3. 🚀 First run test:")
    print(f"   {exe_path}")
    
    print(f"\n4. 📄 Upload your new resume:")
    print(f"   - Launch application")
    print(f"   - Go to 📄 Manage Resumes tab")
    print(f"   - Click ⬆️ Upload New Resume")
    print(f"   - Select your updated resume")
    print(f"   - Click ✅ Set as Active")

def verify_environment():
    """Verifies build environment."""
    print("🔍 Verifying build environment...")
    
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]}")
    
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found. Install: pip install pyinstaller")
        sys.exit(1)
    
    try:
        import PIL.Image
        print(f"✅ Pillow (for icon conversion)")
    except ImportError:
        print("⚠️  Pillow not installed (optional, for icon conversion)")
    
    if not Path('gui/tkinter_app.py').exists():
        print("❌ gui/tkinter_app.py not found")
        sys.exit(1)
    print("✅ Main GUI script found")
    
    assets_dir = Path('assets')
    assets_dir.mkdir(exist_ok=True)
    
    png_path = assets_dir / "icon.png"
    ico_path = assets_dir / "icon.ico"
    icns_path = assets_dir / "icon.icns"
    
    if png_path.exists():
        print(f"✅ Source icon: {png_path}")
    if ico_path.exists():
        print(f"✅ Windows icon: {ico_path} (will be used for Windows builds)")
    if icns_path.exists():
        print(f"✅ macOS icon: {icns_path} (will be used for macOS builds)")
    
    if not Path('.env').exists():
        print("⚠️  Warning: .env file not found - app won't run without it")
    else:
        print("✅ .env configuration file found")
    
    print()

def main():
    """Main build orchestration."""
    parser = argparse.ArgumentParser(
        description='Build Job Application Bot standalone executable',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 build_standalone.py --clean      # Force clean build
  python3 build_standalone.py --no-shortcut # Skip desktop shortcuts
        """
    )
    parser.add_argument('--clean', action='store_true', help='Force clean build')
    parser.add_argument('--no-shortcut', action='store_true', help='Skip desktop shortcut creation')
    args = parser.parse_args()
    
    print("🏗️  Building Job Application Bot Standalone Executable")
    print("=" * 60)
    
    # Pre-flight checks
    verify_environment()
    
    # Clean build artifacts if requested
    if args.clean:
        clean_build_artifacts()
    
    # Find and prepare the best available icon
    icon_path = find_best_icon_for_platform()
    
    # Construct PyInstaller command
    pyinstaller_cmd = get_pyinstaller_command(icon_path, clean=args.clean)
    
    print("\n⚙️  Running PyInstaller...")
    print(f"   Command: pyinstaller {' '.join(pyinstaller_cmd)}")
    
    try:
        # Execute the build
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_cmd)
        
        print("\n✅ Build completed successfully!")
        exe_name = "JobApplicationBot.exe" if sys.platform.startswith('win') else "JobApplicationBot"
        print(f"📁 Executable location: ./{Path('dist') / exe_name}")
        
        # Create desktop integration
        if not args.no_shortcut:
            print("\n🎯 Creating desktop integration...")
            if sys.platform.startswith('win'):
                create_windows_shortcut()
            elif sys.platform == 'darwin':
                print("   macOS: Drag .app from ./dist/ to Applications folder, then to Dock")
            elif sys.platform.startswith('linux'):
                create_linux_desktop_entry()
        
        # Print post-build instructions
        post_build_instructions()
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

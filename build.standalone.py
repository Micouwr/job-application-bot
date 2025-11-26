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

USAGE:
    python build_standalone.py
    python build_standalone.py --clean  # Force clean build
"""

import argparse
import os
import shutil
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

def check_and_create_icon() -> Optional[Path]:
    """
    Checks for icon file and creates it if missing.
    Returns Path to icon file or None if not found.
    """
    icon_dir = Path("gui")
    icon_dir.mkdir(exist_ok=True)
    
    # Platform-specific icon extensions
    is_windows = sys.platform.startswith('win')
    icon_name = "icon.ico" if is_windows else "icon.icns"
    icon_path = icon_dir / icon_name
    
    if not icon_path.exists():
        print(f"⚠️  Icon not found: {icon_path}")
        print("   For best results, create a 256x256 PNG and convert:")
        print("   - Windows: Use online converter → .ico")
        print("   - macOS: Use 'iconutil' → .icns")
        print("   - Linux: .png works directly")
        print("   Place file in ./gui/ directory")
        return None
    
    print(f"✅ Found icon: {icon_path}")
    return icon_path

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
    
    # Add data files and directories
    # Format: source_path:dest_path (separator is ; on Windows, : on Linux/macOS)
    separator = ';' if sys.platform.startswith('win') else ':'
    
    # Core directories
    data_mappings = [
        ('config', 'config'),
        ('data', 'data'),
        ('logs', 'logs'),
        ('output', 'output'),
        ('.env', '.'),  # Must be in root for config loader
    ]
    
    for src, dest in data_mappings:
        if Path(src).exists():
            cmd.extend(['--add-data', f'{src}{separator}{dest}'])
            print(f"   Added data: {src} → {dest}")
    
    # Add individual config file if not already covered
    if Path('config/settings.py').exists():
        cmd.extend(['--add-data', f'config/settings.py{separator}config'])
    
    # Hidden imports for packages that PyInstaller might miss
    hidden_imports = [
        'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.ext.declarative',
        'google.genai', 'google.genai.types',
        'tiktoken', 'tiktoken_ext',
        'PyPDF2',
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
            '--target-architecture', 'universal2',  # Intel + Apple Silicon
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
    Makes the .exe look more professional in file properties.
    """
    try:
        version_content = """# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Ryan Micou'),
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
        desktop_file = Path.home() / ".local/share/applications/JobApplicationBot.desktop"
        desktop_file.parent.mkdir(exist_ok=True)
        
        icon_path = Path("gui/icon.png")
        if not icon_path.exists():
            # Create a simple text icon if none exists
            icon_path = Path("gui/icon.png")
            # This is a placeholder - in real use, create a PNG
        
        exec_path = Path("dist/JobApplicationBot").absolute()
        
        content = f"""[Desktop Entry]
Name=Job Application Bot
Comment=AI-Powered Resume Tailorer
Exec={exec_path}
Icon={icon_path.absolute()}
Terminal=false
Type=Application
Categories=Office;Utility;
StartupNotify=true
Keywords=job;resume;ai;career;
"""
        
        desktop_file.write_text(content)
        desktop_file.chmod(0o755)
        
        print(f"🎯 Linux desktop entry created: {desktop_file}")
        print(f"   You may need to log out/in to see it in applications menu")
        
    except Exception as e:
        print(f"⚠️  Could not create desktop entry: {e}")

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
    
    # Check main script
    if not Path('gui/tkinter_app.py').exists():
        print("❌ gui/tkinter_app.py not found")
        sys.exit(1)
    print("✅ Main script found")
    
    # Check .env
    if not Path('.env').exists():
        print("⚠️  .env file not found. Build will succeed but app won't run without it.")
    else:
        print("✅ .env file found")
    
    print()

def main():
    """Main build orchestration."""
    parser = argparse.ArgumentParser(description='Build Job Application Bot standalone executable')
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
    
    # Check icon
    icon_path = check_and_create_icon()
    
    # Get PyInstaller command
    pyinstaller_cmd = get_pyinstaller_command(icon_path, clean=args.clean)
    
    print("\n⚙️  Running PyInstaller...")
    print(f"   Command: pyinstaller {' '.join(pyinstaller_cmd)}")
    
    try:
        # Import and run PyInstaller programmatically
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_cmd)
        
        print("\n✅ Build completed successfully!")
        print(f"📁 Executable location: ./{'dist/JobApplicationBot.exe' if sys.platform.startswith('win') else 'dist/JobApplicationBot'}")
        
        # Create shortcuts/desktop entries
        if not args.no_shortcut:
            print("\n🎯 Creating desktop integration...")
            if sys.platform.startswith('win'):
                create_windows_shortcut()
            elif sys.platform == 'darwin':
                print("   macOS: Drag .app from ./dist/ to Applications folder")
            elif sys.platform.startswith('linux'):
                create_linux_desktop_entry()
        
        print("\n🎉 Build complete! You can now distribute the executable.")
        print("\nNext steps:")
        print("   1. Test the executable: ./dist/JobApplicationBot")
        print("   2. Copy .env file to same directory if not bundled")
        print("   3. Create installer or zip for distribution")
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

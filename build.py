#!/usr/bin/env python3
"""
Job Application Bot - Production Build Script
Cross-platform: macOS (.app bundle), Windows (.exe), Linux (binary)
"""

import os
import sys
import argparse
import platform
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional

# Required packages:
# pip install pyinstaller Pillow

class Colors:
    """Cross-platform ANSI colors"""
    CYAN = '\033[96m' if sys.platform != 'win32' else ''
    GREEN = '\033[92m' if sys.platform != 'win32' else ''
    YELLOW = '\033[93m' if sys.platform != 'win32' else ''
    RED = '\033[91m' if sys.platform != 'win32' else ''
    BOLD = '\033[1m' if sys.platform != 'win32' else ''
    END = '\033[0m' if sys.platform != 'win32' else ''


def print_section(title: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{title}{Colors.END}")
    print("=" * 60)


def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def check_dependencies():
    """Verify all build dependencies"""
    print_section("🔍 Verifying build dependencies...")

    deps_ok = True

    # Check PyInstaller
    try:
        import PyInstaller
        print_success(f"PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print_error("PyInstaller not installed: pip install pyinstaller")
        deps_ok = False

    # Check Pillow
    try:
        from PIL import Image
        print_success("Pillow (image processing)")
    except ImportError:
        print_error("Pillow not installed: pip install Pillow")
        deps_ok = False

    # Check required project files
    required_files = [
        Path("gui_app.py"),
        Path("config/settings.py"),
        Path("utils/paths.py"),
        Path("assets/icon.png"),
    ]

    for file_path in required_files:
        if file_path.exists():
            print_success(f"Found: {file_path}")
        else:
            print_error(f"Missing: {file_path}")
            deps_ok = False

    # Check platform-specific icons
    if platform.system() == "Darwin" and not Path("assets/icon.icns").exists():
        print_warning("macOS icon.icns will be generated from icon.png")

    if platform.system() == "Windows" and not Path("assets/icon.ico").exists():
        print_warning("Windows icon.ico not found")

    return deps_ok


def convert_icon_for_macos():
    """Convert PNG to ICNS for macOS"""
    icon_png = Path("assets/icon.png")
    icon_icns = Path("assets/icon.icns")

    if icon_icns.exists():
        return icon_icns

    if not icon_png.exists():
        raise RuntimeError("Need assets/icon.png to create macOS icon")

    print_section("🔄 Converting PNG to ICNS...")

    iconset_dir = Path("build/icon.iconset")
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True)

    try:
        from PIL import Image

        # macOS icon sizes
        sizes = {
            'icon_16x16.png': 16, 'icon_16x16@2x.png': 32,
            'icon_32x32.png': 32, 'icon_32x32@2x.png': 64,
            'icon_128x128.png': 128, 'icon_128x128@2x.png': 256,
            'icon_256x256.png': 256, 'icon_256x256@2x.png': 512,
            'icon_512x512.png': 512, 'icon_512x512@2x.png': 1024,
        }

        with Image.open(icon_png) as img:
            for filename, size in sizes.items():
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(iconset_dir / filename)

        subprocess.run(['iconutil', '-c', 'icns', str(iconset_dir)], check=True)
        shutil.move("build/icon.icns", icon_icns)
        shutil.rmtree(iconset_dir)

        print_success(f"Created: {icon_icns}")
        return icon_icns

    except Exception as e:
        print_error(f"Icon conversion failed: {e}")
        raise


def generate_spec_file():
    """Generate PyInstaller spec file if missing"""
    spec_path = Path("job_application_bot.spec")

    if spec_path.exists():
        print_success(f"Found existing spec: {spec_path}")
        return spec_path

    print_section("⚙️  Generating spec file...")

    system = platform.system()
    is_macos = system == "Darwin"
    is_windows = system == "Windows"

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

# Platform detection
IS_MACOS = {is_macos}
IS_WINDOWS = {is_windows}

block_cipher = None

hidden_imports = [
    # GUI
    'tkinter', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.ttk', 'tkinter.scrolledtext',

    # PDF/DOCX
    'PyPDF2', 'PyPDF2._reader', 'PyPDF2.generic', 'PyPDF2._crypter',
    'docx', 'docx.document', 'docx.opc.constants', 'docx.oxml', 'docx.enum.text',
    'docx.enum.style', 'docx.shared', 'docx.image', 'docx.image.exceptions',

    # Database
    'sqlalchemy', 'sqlalchemy.dialects.sqlite', 'sqlalchemy.pool', 'sqlalchemy.orm',
    'sqlalchemy.ext.declarative',

    # AI
    'google.generativeai', 'google.generativeai.types', 'google.ai.generativelanguage',
    'tiktoken', 'tiktoken_ext',

    # Other
    'pydantic', 'pydantic_core', 'dotenv', 'tqdm', 'requests', 'beautifulsoup4',
]

added_files = [
    ('config', 'config'),
    ('utils', 'utils'),
    ('gui', 'gui'),
    ('assets', 'assets'),
    ('resume.json.template', '.'),
    ('.env.example', '.'),
]

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['pytest', 'test', 'tests', 'unittest', 'doctest', 'matplotlib', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='JobApplicationBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False,
    upx=True,
    name='JobApplicationBot',
)

# macOS app bundle
if IS_MACOS:
    app = BUNDLE(
        coll,
        name='JobApplicationBot.app',
        icon='assets/icon.icns',
        bundle_identifier='com.micouwr.jobapplicationbot',
        version='1.0.0',
        info_plist={{
            'CFBundleName': 'Job Application Bot',
            'CFBundleDisplayName': 'Job Application Bot',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
            'LSMinimumSystemVersion': '10.12',
            'NSAppTransportSecurity': {{'NSAllowsArbitraryLoads': True}},
        }},
    )
'''

    spec_path.write_text(spec_content)
    print_success(f"Generated: {spec_path}")
    return spec_path


def build_application(clean: bool = False):
    """Build using spec file"""
    if clean:
        print_section("🧹 Cleaning...")
        shutil.rmtree("build", ignore_errors=True)
        shutil.rmtree("dist", ignore_errors=True)

    # Generate spec if needed
    spec_path = generate_spec_file()

    # Convert icon for macOS
    if platform.system() == "Darwin":
        convert_icon_for_macos()

    print_section("🔨 Building with PyInstaller...")

    cmd = ['pyinstaller', '--clean', '--noconfirm', str(spec_path)]

    try:
        subprocess.run(cmd, check=True)
        print_success("Build completed!")

        # Show results
        print_section("📦 Build Results")
        system = platform.system()

        if system == "Darwin":
            app_path = Path("dist/JobApplicationBot.app")
            if app_path.exists():
                print_success(f"macOS App: {app_path}")
                size = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file()) / 1024 / 1024
                print(f"   Size: {size:.1f} MB")
                print_warning("Users must create their own .env file at:")
                print("   ~/Library/Application Support/JobApplicationBot/.env")

        elif system == "Windows":
            exe_path = Path("dist/JobApplicationBot/JobApplicationBot.exe")
            if exe_path.exists():
                print_success(f"Windows EXE: {exe_path}")
                print_warning("Users must create their own .env file in the same directory")

        else:  # Linux
            exe_path = Path("dist/JobApplicationBot/JobApplicationBot")
            if exe_path.exists():
                print_success(f"Linux Binary: {exe_path}")

        return True

    except subprocess.CalledProcessError as e:
        print_error(f"Build failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Build Job Application Bot for macOS/Windows/Linux",
        epilog="Examples:\n  python build.py                    # Build for current platform\n  python build.py --clean            # Clean before build"
    )
    parser.add_argument('--clean', action='store_true', help="Clean build artifacts before building")
    args = parser.parse_args()

    if not check_dependencies():
        sys.exit(1)

    success = build_application(clean=args.clean)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

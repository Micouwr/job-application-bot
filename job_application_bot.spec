# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Critical hidden imports for all dependencies
hidden_imports = [
    # Document parsing
    'PyPDF2', 'PyPDF2._reader', 'PyPDF2._utils', 'PyPDF2.errors',
    'docx', 'docx.api', 'docx.package', 'docx.parts', 'docx.parts.document',
    'docx.oxml', 'docx.oxml.coreprops', 'docx.text', 'docx.enum',
    'lxml', 'lxml._elementpath', 'lxml.etree',
    # PDF generation
    'reportlab', 'reportlab.lib.pagesizes', 'reportlab.platypus',
    'reportlab.lib.styles', 'reportlab.lib.units',
    # Image handling
    'PIL', 'PIL.Image', 'PIL.ImageFile',
    # Template engine
    'jinja2', 'jinja2.ext', 'jinja2.bccache',
    # Database
    'sqlalchemy.ext.declarative',
    # AI/NLP tokenization
    'tiktoken', 'tiktoken_ext',
]

# Data files to bundle - resume.json.template is in ROOT
datas = [
    ('resume.json.template', '.'),  # Copy to bundle root
    ('entitlements.plist', '.'),
    ('assets/icon.png', 'assets/'),
]

a = Analysis(
    ['gui/tkinter_app.py'],  # Entry point
    pathex=[str(Path('.').absolute())],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test', 'unittest', 'pytest', 'pydoc', 'doctest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JobApplicationBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # Critical for macOS file dialogs
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements.plist' if sys.platform == 'darwin' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll', 'ucrtbase.dll', 'python311.dll',
        'cryptography.hazmat.bindings._openssl', '_cffi_backend'
    ],
    name='JobApplicationBot',
)

# macOS app bundle configuration
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='JobApplicationBot.app',
        icon='assets/icon.icns' if Path('assets/icon.icns').exists() else None,
        bundle_identifier='com.micouwr.jobapplicationbot',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'NSRequiresAquaSystemAppearance': 'False',
            'CFBundleShortVersionString': '2.0.0',
            'CFBundleVersion': '200',
            'NSHumanReadableCopyright': 'Copyright © 2024 Micouwr',
            'NSDesktopFolderUsageDescription': 'Save tailored job applications',
            'NSDocumentsFolderUsageDescription': 'Access resume and cover letter files',
        },
        entitlements_file='entitlements.plist',
    )

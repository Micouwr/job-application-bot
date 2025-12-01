#!/usr/bin/env python3
"""
Job Application Bot - Simplified Build Script
Uses the spec file for all configuration
"""

import sys
import subprocess
from pathlib import Path

def build_application():
    """Build using the spec file"""
    print("🔨 Building Job Application Bot...")
    
    spec_path = Path('job_application_bot.spec')
    if not spec_path.exists():
        print("❌ job_application_bot.spec not found in project root!")
        sys.exit(1)
    
    # Clean previous builds
    print("🧹 Cleaning previous builds...")
    subprocess.run(['rm', '-rf', 'build', 'dist'], stderr=subprocess.DEVNULL)
    
    # Run PyInstaller with spec
    try:
        subprocess.run([
            'pyinstaller',
            'job_application_bot.spec',
            '--clean',
            '--noconfirm',
            '--distpath', './dist',
            '--workpath', './build'
        ], check=True)
        
        print("✅ Build completed successfully!")
        
        # Verify output
        dist_dir = Path('dist')
        if sys.platform == 'darwin':
            app_path = dist_dir / 'JobApplicationBot.app'
            if app_path.exists():
                print(f"📦 macOS app bundle: {app_path}")
                print(f"   Test with: {app_path}/Contents/MacOS/JobApplicationBot")
            else:
                print("❌ macOS app bundle not found!")
        elif sys.platform == 'win32':
            exe_path = dist_dir / 'JobApplicationBot' / 'JobApplicationBot.exe'
            if exe_path.exists():
                print(f"📦 Windows executable: {exe_path}")
            else:
                print("❌ Windows executable not found!")
        else:
            exe_path = dist_dir / 'JobApplicationBot' / 'JobApplicationBot'
            if exe_path.exists():
                print(f"📦 Linux executable: {exe_path}")
            else:
                print("❌ Linux executable not found!")
                
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller failed: {e}")
        print("   Check the build log in ./build/ for details")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_application()

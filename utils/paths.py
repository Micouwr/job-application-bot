import sys
import os
from pathlib import Path

def get_base_path() -> Path:
    """Get application base path that works both in dev and PyInstaller bundle"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running in development
        return Path(__file__).resolve().parent.parent

def get_user_data_path() -> Path:
    """
    Get user-writable data directory that is native to the OS.
    - macOS: ~/Library/Application Support/JobApplicationBot
    - Windows: C:/Users/<user>/AppData/Roaming/JobApplicationBot
    - Linux: ~/.config/JobApplicationBot or ~/.job_application_bot
    """
    if sys.platform == 'darwin':
        # macOS
        return Path.home() / 'Library' / 'Application Support' / 'JobApplicationBot'
    elif sys.platform == 'win32':
        # Windows
        appdata = os.getenv('APPDATA')
        if appdata:
            return Path(appdata) / 'JobApplicationBot'
        else:
            # Fallback if APPDATA is not set
            return Path.home() / 'JobApplicationBot'
    else:
        # Linux and other Unix-like systems
        # Use XDG_CONFIG_HOME if available, otherwise fallback to ~/.config
        xdg_config_home = os.getenv('XDG_CONFIG_HOME')
        if xdg_config_home:
            return Path(xdg_config_home) / 'JobApplicationBot'
        else:
            # Fallback to a hidden directory in the user's home
            return Path.home() / '.job_application_bot'

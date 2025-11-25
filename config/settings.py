"""
Configuration settings for Job Application Bot - Enterprise Grade
Handles environment validation, path resolution, and security.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

# ==========================================
# PATH RESOLUTION (PyInstaller Compatible)
# ==========================================

def _get_base_dir() -> Path:
    """
    Get base directory that works both in development and PyInstaller bundles.
    Prevents path traversal attacks by ensuring we stay in project scope.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        base_dir = Path(sys.executable).parent
    else:
        # Running from source
        base_dir = Path(__file__).resolve().parent.parent
    
    return base_dir

BASE_DIR = _get_base_dir()

# ==========================================
# ENVIRONMENT VALIDATION (Critical Security)
# ==========================================

def validate_config() -> bool:
    """
    Validates all required configuration before bot starts.
    Provides clear, actionable error messages.
    Returns True if valid, raises ValueError if not.
    """
    errors = []
    warnings = []
    
    # 1. Check .env file exists
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        if (BASE_DIR / ".env.example").exists():
            errors.append(
                f".env file not found at {env_path}. "
                f"Copy .env.example to .env and add your API key:\n"
                f"  cp .env.example .env"
            )
        else:
            errors.append(
                f"No .env file found at {env_path}. Create one from .env.example"
            )
    
    # 2. Load and validate API keys
    load_dotenv(env_path)
    
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        errors.append("GEMINI_API_KEY is not set in .env file")
    elif not re.match(r'^AIza[0-9A-Za-z_-]{35,}$', gemini_key):
        errors.append(
            "GEMINI_API_KEY format is invalid. Must start with 'AIza' and be ~40+ characters. "
            "Get your key from: https://makersuite.google.com/app/apikey"
        )
    
    # 3. Validate required user information
    required_fields = {
        "YOUR_NAME": "Your full name",
        "YOUR_EMAIL": "Your email address"
    }
    
    for field, description in required_fields.items():
        value = os.getenv(field, "").strip()
        if not value:
            errors.append(f"{field} ({description}) is not set in .env file")
        elif

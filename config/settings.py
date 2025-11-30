"""
Configuration settings for Job Application Bot using Pydantic for validation.
This module is now architected to work correctly in both development
and a bundled PyInstaller application, with cross-platform support.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings

# CRITICAL: Import the enhanced cross-platform pathing utility
from utils.paths import get_base_path, get_user_data_path

# --- Path Definitions ---

# Base path for bundled data files (works in dev and bundle)
BASE_DIR = get_base_path()

# User-writable directory for database, logs, etc. (works for macOS, Windows, Linux)
USER_DATA_DIR = get_user_data_path()

# Define user-writable subdirectories
DATA_DIR: Path = USER_DATA_DIR / "data"
LOGS_DIR: Path = USER_DATA_DIR / "logs"
OUTPUT_DIR: Path = USER_DATA_DIR / "output"
RESUMES_DIR: Path = USER_DATA_DIR / "resumes"
COVER_LETTERS_DIR: Path = OUTPUT_DIR / "cover_letters"

# Platform-specific log directory for macOS (as per best practice)
if sys.platform == 'darwin':
    LOGS_DIR = Path.home() / 'Library' / 'Logs' / 'JobApplicationBot'

# Create all user-writable directories on startup
for directory in [USER_DATA_DIR, DATA_DIR, LOGS_DIR, OUTPUT_DIR, RESUMES_DIR, COVER_LETTERS_DIR]:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        # Verify directory is writable
        if not os.access(directory, os.W_OK):
            raise OSError(f"Directory {directory} is not writable!")
    except (OSError, PermissionError) as e:
        print(f"❌ CRITICAL ERROR: Could not create or write to required directory: {directory}")
        print(f"   Reason: {e}")
        print("   Please check permissions and try again.")
        sys.exit(1)


# --- Two-Tier .env Loading ---
# 1. Look for a .env file in the user's data directory (for user overrides)
# 2. Fall back to the bundled .env.example (for default settings)
env_paths_to_check = [
    USER_DATA_DIR / '.env',
    BASE_DIR / '.env.example' # Bundled fallback
]

loaded_env = False
for env_path in env_paths_to_check:
    if env_path.exists():
        print(f"ℹ️ Loading configuration from: {env_path}")
        load_dotenv(env_path)
        loaded_env = True
        break

if not loaded_env:
    print("❌ CRITICAL: No .env or .env.example file found. Please create one.")
    sys.exit(1)


class JobSearchConfig(BaseSettings):
    """
    Pydantic model for job search configuration with validation.
    """
    # --- API Keys ---
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY", description="Google Gemini API Key")
    scraper_api_key: Optional[str] = Field(None, alias="SCRAPER_API_KEY", description="ScraperAPI Key (Optional)")

    # --- Job Search Settings ---
    job_location: str = Field("Louisville, KY", alias="JOB_LOCATION")
    max_jobs_per_platform: int = Field(50, alias="MAX_JOBS_PER_PLATFORM", ge=1, le=1000)
    match_threshold: float = Field(0.80, alias="MATCH_THRESHOLD", ge=0.0, le=1.0)

    # --- Personal Information ---
    your_name: str = Field(..., alias="YOUR_NAME", min_length=1)
    your_email: str = Field(..., alias="YOUR_EMAIL", pattern=r"^[^@]+@[^@]+\.[^@]+$")
    your_phone: str = Field(..., alias="YOUR_PHONE", min_length=10)
    your_linkedin: str = Field("linkedin.com/in/yourprofile", alias="YOUR_LINKEDIN")
    your_github: str = Field("github.com/yourusername", alias="YOUR_GITHUB")

    # --- Logging ---
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    model: str = Field("gemini-1.5-flash", alias="MODEL")

    class Config:
        # We no longer specify env_file here since we load it manually above
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        if not v or not v.startswith("AIza"):
            raise ValueError("GEMINI_API_KEY must be a valid Google API key starting with 'AIza'")
        if len(v) != 39:
            raise ValueError("GEMINI_API_KEY must be 39 characters long")
        return v

    @field_validator("scraper_api_key")
    @classmethod
    def validate_scraper_key(cls, v: Optional[str]) -> Optional[str]:
        if v and (len(v) < 20 or not v[0].isalpha()):
            raise ValueError("SCRAPER_API_KEY appears to be invalid format")
        return v


# Safe configuration initialization with error handling
try:
    config = JobSearchConfig()
except ValidationError as e:
    print("❌ Configuration validation failed:")
    for error in e.errors():
        field = error['loc'][0] if error['loc'] else 'unknown'
        print(f"  {field}: {error['msg']}")
    print("\nPlease check your .env file and try again.")
    sys.exit(1)


# --- Export configuration values for backward compatibility and quick access ---
GEMINI_API_KEY: str = config.gemini_api_key
SCRAPER_API_KEY: Optional[str] = config.scraper_api_key
JOB_LOCATION: str = config.job_location
MAX_JOBS_PER_PLATFORM: int = config.max_jobs_per_platform
MATCH_THRESHOLD: float = config.match_threshold

YOUR_INFO: Dict[str, str] = {
    "name": config.your_name,
    "email": config.your_email,
    "phone": config.your_phone,
    "linkedin": config.your_linkedin,
    "github": config.your_github,
    "location": config.job_location,
}


# --- Core Application Constants ---

# Database (now points to user-writable directory)
DATABASE_PATH: Path = DATA_DIR / "job_applications.db"

# Logging (now points to user-writable directory)
LOG_FILE: Path = LOGS_DIR / "job_application.log"
LOG_LEVEL: str = config.log_level

# Job Search Keywords
JOB_KEYWORDS: List[str] = [
    "IT Infrastructure Architect", "Senior Infrastructure Architect", "AI Governance",
    "ISO 42001", "Cloud Infrastructure Architect", "Systems Architect",
    "Service Desk Manager", "Technical Support Manager",
]

# Scraping Settings
SCRAPING: Dict[str, Any] = {
    "headless": True, "timeout": 30000, "delay_between_requests": 2,
    "max_retries": 3, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Matching Settings
MATCHING: Dict[str, Any] = {
    "threshold": MATCH_THRESHOLD,
    "weights": {"skills": 0.40, "experience": 0.40, "keywords": 0.20},
    "experience_level_multiplier": 0.85,
}

# --- Resume Data Loading (now uses get_base_path) ---
def load_resume_data() -> Dict[str, Any]:
    """
    Loads resume from user directory, copying a template on first launch.
    This ensures user data is never bundled with the application.
    """
    user_resume_path = USER_DATA_DIR / "resume.json"
    template_resume_path = BASE_DIR / "resume.json.template"

    # First launch: copy the template to the user's data directory
    if not user_resume_path.exists():
        if template_resume_path.exists():
            try:
                shutil.copy(template_resume_path, user_resume_path)
                print(f"✅ Created user resume file at: {user_resume_path}")
            except (IOError, OSError) as e:
                print(f"❌ CRITICAL: Could not copy resume template: {e}")
                sys.exit(1)
        else:
            print(f"❌ CRITICAL: Resume template not found at {template_resume_path}")
            sys.exit(1)

    # Always load from the user's data directory
    try:
        with open(user_resume_path, 'r', encoding='utf-8') as f:
            import json
            data = json.load(f)

        # Inject the personal information from the validated config
        data["personal"] = YOUR_INFO
        return data
    except (Exception, json.JSONDecodeError) as e:
        print(f"❌ CRITICAL: Failed to load or parse user's resume.json: {e}")
        sys.exit(1)

RESUME_DATA: Dict[str, Any] = load_resume_data()

def get_config() -> JobSearchConfig:
    """ Get the Pydantic configuration object """
    return config

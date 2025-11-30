"""
Configuration settings for Job Application Bot using Pydantic for validation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
LOGS_DIR: Path = BASE_DIR / "logs"
OUTPUT_DIR: Path = BASE_DIR / "output"
RESUMES_DIR: Path = OUTPUT_DIR / "resumes"
COVER_LETTERS_DIR: Path = OUTPUT_DIR / "cover_letters"

# Create directories if they don't exist
for directory in [DATA_DIR, LOGS_DIR, OUTPUT_DIR, RESUMES_DIR, COVER_LETTERS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

    # Verify directory is writable
    if not os.access(directory, os.W_OK):
        print(f"❌ Error: Directory {directory} is not writable!")
        print("Please check permissions and try again.")
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
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Validate Gemini API key format (strict check for common developer key)"""
        if not v or not v.startswith("AIza"):
            raise ValueError("GEMINI_API_KEY must be a valid Google API key starting with 'AIza'")
        if len(v) != 39:
            raise ValueError("GEMINI_API_KEY must be 39 characters long")
        return v

    @field_validator("scraper_api_key")
    @classmethod
    def validate_scraper_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate ScraperAPI key format if provided"""
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


# Export configuration values for backward compatibility and quick access
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

# Job Search Keywords (Optimized for AI/Architectural Transition)
JOB_KEYWORDS: List[str] = [
    "IT Infrastructure Architect",
    "Senior Infrastructure Architect",
    "AI Governance",
    "ISO 42001",
    "Cloud Infrastructure Architect",
    "Systems Architect",
    "Service Desk Manager",
    "Technical Support Manager",
]

# Database
DATABASE_PATH: Path = DATA_DIR / "job_applications.db"

# Logging
LOG_FILE: Path = LOGS_DIR / "job_application.log"
LOG_LEVEL: str = config.log_level

# Scraping Settings
SCRAPING: Dict[str, Any] = {
    "headless": True,
    "timeout": 30000,  # milliseconds
    "delay_between_requests": 2,  # seconds
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Matching Settings
MATCHING: Dict[str, Any] = {
    "threshold": MATCH_THRESHOLD,
    # High weights ensure alignment with core resume sections is prioritized
    "weights": {"skills": 0.40, "experience": 0.40, "keywords": 0.20},
    "experience_level_multiplier": 0.85,  # Applied if level doesn't match
}

# --- Resume Data Loading ---
def load_resume_data() -> Dict[str, Any]:
    """Loads the resume data from the JSON file and injects personal info."""
    resume_file = BASE_DIR / "resume.json"
    if not resume_file.exists():
        print("❌ CRITICAL: resume.json not found! Please create it.")
        sys.exit(1)

    try:
        with open(resume_file, 'r', encoding='utf-8') as f:
            import json
            data = json.load(f)

        # Inject the personal information from the validated config
        data["personal"] = YOUR_INFO
        return data
    except Exception as e:
        print(f"❌ CRITICAL: Failed to load or parse resume.json: {e}")
        sys.exit(1)

RESUME_DATA: Dict[str, Any] = load_resume_data()


def validate_config() -> bool:
    """ Legacy validation function - now handled by Pydantic """
    return True

def get_config() -> JobSearchConfig:
    """ Get the Pydantic configuration object """
    return config
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
    
    # ✅ QoL: Verify directory is writable
    if not os.access(directory, os.W_OK):
        print(f"❌ Error: Directory {directory} is not writable!")
        print("Please check permissions and try again.")
        sys.exit(1)


class JobSearchConfig(BaseSettings):
    """
    Pydantic model for job search configuration with validation.
    """
    
    # API Keys
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY", description="Google Gemini API Key")
    scraper_api_key: Optional[str] = Field(None, alias="SCRAPER_API_KEY", description="ScraperAPI Key")
    
    # Job Search Settings
    job_location: str = Field("Louisville, KY", alias="JOB_LOCATION")
    max_jobs_per_platform: int = Field(50, alias="MAX_JOBS_PER_PLATFORM", ge=1, le=1000)
    match_threshold: float = Field(0.80, alias="MATCH_THRESHOLD", ge=0.0, le=1.0)
    
    # Personal Information
    your_name: str = Field(..., alias="YOUR_NAME", min_length=1)
    your_email: str = Field(..., alias="YOUR_EMAIL", pattern=r"^[^@]+@[^@]+\.[^@]+$")
    your_phone: str = Field(..., alias="YOUR_PHONE", min_length=10)
    your_linkedin: str = Field("linkedin.com/in/yourprofile", alias="YOUR_LINKEDIN")
    your_github: str = Field("github.com/yourusername", alias="YOUR_GITHUB")
    
    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # ✅ QoL: Handle case variations like Gemini_API_Key

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Validate Gemini API key format"""
        if not v or not v.startswith("AIza"):
            raise ValueError("GEMINI_API_KEY must be a valid Google API key starting with 'AIza'")
        if len(v) != 39:
            raise ValueError("GEMINI_API_KEY must be 39 characters long")
        return v

    @field_validator("scraper_api_key")
    @classmethod
    def validate_scraper_key(cls, v: Optional[str]) -> Optional[str]:
        """ ✅ QoL: Validate ScraperAPI key format if provided """
        if v:
            # ScraperAPI keys typically start with specific prefixes
            if len(v) < 20 or not v[0].isalpha():
                raise ValueError("SCRAPER_API_KEY appears to be invalid format")
        return v


# ✅ QoL: Safe configuration initialization with error handling
try:
    config = JobSearchConfig()
except ValidationError as e:
    print("❌ Configuration validation failed:")
    for error in e.errors():
        field = error['loc'][0] if error['loc'] else 'unknown'
        print(f"  {field}: {error['msg']}")
    print("\nPlease check your .env file and try again.")
    sys.exit(1)


# Export configuration values for backward compatibility with error handling
try:
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
        "github": config.your_github,  # ✅ Fixed forward slash
        "location": config.job_location,
    }
except Exception as e:
    print(f"❌ Error accessing configuration: {e}")
    sys.exit(1)

# Job Search Keywords
JOB_KEYWORDS: List[str] = [
    "IT Infrastructure Architect",
    "Senior Infrastructure Architect",
    "Help Desk Manager",
    "Service Desk Manager",
    "Technical Support Manager",
    "IT Support Manager",
    "AI Governance",
    "Cloud Infrastructure Architect",
    "Systems Architect",
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
    "weights": {"skills": 0.40, "experience": 0.40, "keywords": 0.20},
    "experience_level_multiplier": 0.85,  # Applied if level doesn't match
}

# Tailoring Settings
TAILORING: Dict[str, Any] = {
    "max_tokens": 4000,
    "temperature": 0.7,
    "model": "gemini-2.5-flash",
}

# Resume Data Structure - ✅ Fixed regular hyphens in dates
RESUME_DATA: Dict[str, Any] = {
    "personal": YOUR_INFO,
    "summary": "Senior IT Infrastructure Architect with 20+ years bridging legacy systems and modern cloud platforms. Certified in AI governance (ISO/IEC 42001), generative AI, and cloud fundamentals.",
    "skills": {
        "ai_cloud": [
            "AI Governance",
            "ISO/IEC 42001",
            "Prompt Engineering",
            "AWS Cloud Infrastructure",
            "Generative AI",
        ],
        "infrastructure_security": [
            "Network Security",
            "Cisco Meraki",
            "Identity & Access Management",
            "Active Directory",
            "VPN Configuration",
            "Firewall Configuration",
        ],
        "service_leadership": [
            "Help Desk Leadership",
            "SLA Optimization",
            "Technical Training",
            "Team Leadership",
            "Tier 1-3 Support",
        ],
        "technical": [
            "Python",
            "Linux",
            "Windows Server",
            "CAD/CAM Systems",
            "Automated Testing",
        ],
    },
    "experience": [
        {
            "company": "CIMSystem",
            "title": "Digital Dental Technical Specialist",
            "dates": "2018-2025",  # ✅ Fixed: regular hyphen
            "location": "Louisville, KY",
            "achievements": [
                "Led 10 person help desk supporting ~150 dealer partners, managing CAD/CAM systems and milling machines",
                "Built dealer enablement ecosystem: delivered MillBox 101 program, reducing time-to-first-mill by 50%",
                "Presented technical sessions at Lab Day West conventions (2023-2024) for audiences of 100+ professionals",  # ✅ Fixed: regular hyphen
            ],
            "skills_used": [
                "Help Desk Leadership",
                "Technical Training",
                "Knowledge Base Architecture",
                "Team Leadership",
            ],
        },
        {
            "company": "AccuCode",
            "title": "Network Architect",
            "dates": "2017-2018",
            "location": "Louisville, KY",
            "achievements": [
                "Engineered secure network architecture with Cisco Meraki and Linux imaging, cutting deployment time by 50%",
                "Implemented VPN and firewall configurations supporting distributed workforce",
                "Served as Tier 3 escalation support for field agents",
            ],
            "skills_used": [
                "Network Security",
                "Cisco Meraki",
                "VPN Configuration",
                "Tier 3 Support",
            ],
        },
        {
            "company": "CompuCom (Contract: Booz Allen Hamilton)",
            "title": "Service Desk Analyst and Trainer",
            "dates": "2013-2017",
            "location": "Louisville, KY",
            "achievements": [
                "Delivered Tier 1-2 support for 1,000+ federal and enterprise users",
                "Achieved 90% first-contact resolution, reducing escalations",
                "Developed training curriculum and mentored analysts",
            ],
            "skills_used": [
                "Tier 1-2 Support",
                "Active Directory",
                "Training Curriculum Development",
            ],
        },
    ],
    "projects": [
        {
            "name": "AI Triage Bot Prototype",
            "github": "github.com/Micouwr/AI-TRIAGE_Bot",
            "dates": "November 2025-Present",  # ✅ Fixed: regular hyphen
            "description": "Developed prototype ticket classification engine in Python aligned with ISO/IEC 42001 transparency principles",
            "achievements": [
                "Designed modular system for intelligent routing and PII detection",
                "Implemented automated testing with assertion-based validation",
            ],
        }
    ],
    "certifications": [
        {
            "name": "ISO/IEC 42001:2023 – AI Management System Fundamentals",
            "issuer": "Alison",
            "date": "November 2025",
        },
        {"name": "AWS Cloud Practitioner Essentials", "issuer": "AWS", "date": "2025"},
        {"name": "Google AI Essentials", "issuer": "Coursera", "date": "2025"},
        {"name": "Generative AI Fundamentals", "issuer": "Databricks", "date": "2025"},
        {"name": "CompTIA A+", "issuer": "CompTIA", "status": "Active"},
    ],
    "education": [
        {
            "institution": "Sullivan University",
            "program": "CodeLouisville Graduate – Front-End Web Development",
        },
        {
            "institution": "Western Kentucky University",
            "program": "General Studies Coursework",
        },
    ],
}

def validate_config() -> bool:
    """ Legacy validation function - now handled by Pydantic """
    return True


def get_config() -> JobSearchConfig:
    """ Get the Pydantic configuration object """
    return config

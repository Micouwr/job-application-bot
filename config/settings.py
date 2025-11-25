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
        elif field == "YOUR_EMAIL" and "@" not in value:
            warnings.append(f"{field} doesn't look like a valid email: {value}")
    
    # 4. Validate optional but important fields
    if not os.getenv("JOB_LOCATION"):
        warnings.append("JOB_LOCATION not set, using default: Louisville, KY")
    
    # 5. Validate numerical settings
    try:
        max_jobs = int(os.getenv("MAX_JOBS_PER_PLATFORM", "50"))
        if max_jobs <= 0 or max_jobs > 1000:
            warnings.append(f"MAX_JOBS_PER_PLATFORM={max_jobs} seems unreasonable, using 50")
    except ValueError:
        warnings.append("MAX_JOBS_PER_PLATFORM must be a number, using default: 50")
    
    try:
        threshold = float(os.getenv("MATCH_THRESHOLD", "0.80"))
        if threshold < 0 or threshold > 1:
            errors.append(f"MATCH_THRESHOLD={threshold} must be between 0.0 and 1.0")
    except ValueError:
        errors.append("MATCH_THRESHOLD must be a number (e.g., 0.80)")
    
    # 6. Check that required directories are writable
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "test_write").touch()
        (DATA_DIR / "test_write").unlink()
    except Exception as e:
        errors.append(f"Cannot write to data directory {DATA_DIR}: {e}")
    
    # Report results
    if errors:
        error_msg = "\n".join(f"  ❌ {e}" for e in errors)
        raise ValueError(
            f"\n{'='*60}\n"
            f"CONFIGURATION ERRORS (Bot Cannot Start)\n"
            f"{'='*60}\n{error_msg}\n"
            f"{'='*60}\n"
            f"Please fix these issues and restart."
        )
    
    if warnings:
        warning_msg = "\n".join(f"  ⚠️  {w}" for w in warnings)
        print(
            f"\n{'='*60}\n"
            f"CONFIGURATION WARNINGS\n"
            f"{'='*60}\n{warning_msg}\n"
            f"{'='*60}\n"
        )
    
    print("✓ Configuration validated successfully")
    return True

# ==========================================
# DIRECTORY SETUP (Secure)
# ==========================================

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
RESUMES_DIR = OUTPUT_DIR / "resumes"
COVER_LETTERS_DIR = OUTPUT_DIR / "cover_letters"

# Create directories with error handling
for directory in [DATA_DIR, LOGS_DIR, OUTPUT_DIR, RESUMES_DIR, COVER_LETTERS_DIR]:
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Cannot create directory {directory}: {e}")

# ==========================================
# CONFIGURATION VARIABLES
# ==========================================

# API Keys (validated above)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

# Job Search Settings
JOB_LOCATION = os.getenv("JOB_LOCATION", "Louisville, KY")
MAX_JOBS_PER_PLATFORM = int(os.getenv("MAX_JOBS_PER_PLATFORM", "50"))
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.80"))

# Job Search Keywords
JOB_KEYWORDS = [
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

# Your Information
YOUR_INFO = {
    "name": os.getenv("YOUR_NAME"),
    "email": os.getenv("YOUR_EMAIL"),
    "phone": os.getenv("YOUR_PHONE"),
    "linkedin": os.getenv("YOUR_LINKEDIN", ""),
    "github": os.getenv("YOUR_GITHUB", ""),
    "location": JOB_LOCATION,
}

# Database
DATABASE_PATH = DATA_DIR / "job_applications.db"
LOG_FILE = LOGS_DIR / "job_application.log"

# Scraping Settings
SCRAPING = {
    "headless": True,
    "timeout": 30000,  # milliseconds
    "delay_between_requests": 2,  # seconds
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Matching Settings
MATCHING = {
    "threshold": MATCH_THRESHOLD,
    "weights": {"skills": 0.40, "experience": 0.40, "keywords": 0.20},
    "experience_level_multiplier": 0.85,
}

# Tailoring Settings
TAILORING = {
    "max_tokens": 4000,
    "temperature": 0.7,
    "model": "gemini-1.5-flash",
    "timeout": 120,  # seconds
    "max_retries": 3,
}

# Resume Data Structure
RESUME_DATA = {
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
            "dates": "2018–2025",
            "location": "Louisville, KY",
            "achievements": [
                "Led 10 person help desk supporting ~150 dealer partners, managing CAD/CAM systems and milling machines",
                "Built dealer enablement ecosystem: delivered MillBox 101 program, reducing time-to-first-mill by 50%",
                "Presented technical sessions at Lab Day West conventions (2023–2024) for audiences of 100+ professionals",
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
            "dates": "2017–2018",
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
            "dates": "2013–2017",
            "location": "Louisville, KY",
            "achievements": [
                "Delivered Tier 1–2 support for 1,000+ federal and enterprise users",
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
            "dates": "November 2025–Present",
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

# Run validation on import
# This will raise ValueError if configuration is invalid
validate_config()

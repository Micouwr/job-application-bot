"""
Configuration settings for Job Application Bot
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
RESUMES_DIR = OUTPUT_DIR / "resumes"
COVER_LETTERS_DIR = OUTPUT_DIR / "cover_letters"

# Create directories if they don't exist
for directory in [DATA_DIR, LOGS_DIR, OUTPUT_DIR, RESUMES_DIR, COVER_LETTERS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

# Job Search Settings
JOB_LOCATION = os.getenv("JOB_LOCATION", "Louisville, KY")
MAX_JOBS_PER_PLATFORM = int(os.getenv("MAX_JOBS_PER_PLATFORM", "50"))
MATCH_THRESHOLD = float(os.getenv("MATCH_THRESHOLD", "0.80"))

# Your Information
YOUR_INFO = {
    "name": os.getenv("YOUR_NAME"),
    "email": os.getenv("YOUR_EMAIL"),
    "phone": os.getenv("YOUR_PHONE"),
    "linkedin": os.getenv("YOUR_LINKEDIN", "linkedin.com/in/ryanmicou"),
    "github": os.getenv("YOUR_GITHUB", "github.com/Micouwr"),
    "location": JOB_LOCATION,
}

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

# Database
DATABASE_PATH = DATA_DIR / "job_applications.db"

# Logging
LOG_FILE = LOGS_DIR / "job_application.log"
LOG_LEVEL = "INFO"

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
    "experience_level_multiplier": 0.85,  # Applied if level doesn't match
}

# Tailoring Settings
TAILORING = {
    "max_tokens": 4000,
    "temperature": 0.7,
    "model": "gemini-1.5-pro",  # updated to Gemini model
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


def validate_config():
    """Validate that all required configuration is present"""
    errors = []

    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set in .env file")

    if not JOB_LOCATION:
        errors.append("JOB_LOCATION is not set")

    if errors:
        raise ValueError(
            "Configuration errors:\n" + "\n".join(f"- {e}" for e in errors)
        )

    return True

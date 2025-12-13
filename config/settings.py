import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini AI Model Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Database path
DB_PATH = Path("database/applications.db")

# Output directory for tailored resumes
OUTPUT_PATH = Path("output")

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_api_key_here")

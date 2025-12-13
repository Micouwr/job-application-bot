import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# AI Model Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Workflow Configuration - User sets based on risk tolerance
MIN_MATCH_THRESHOLD = int(os.getenv("MIN_MATCH_THRESHOLD", "80"))  # Default 80%

# Paths
DB_PATH = Path("database/applications.db")
OUTPUT_PATH = Path("output")

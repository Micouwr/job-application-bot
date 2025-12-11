from pathlib import Path

# Base project paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = PROJECT_ROOT / "output"
DB_PATH = PROJECT_ROOT / "database" / "applications.db"
CERTS_PATH = PROJECT_ROOT / "certs"

# API Configuration
GEMINI_API_KEY = ""  # Set via .env file

# Model Configuration (Future-proof: easily upgraded to 2.5-pro)
MODEL_NAME = "gemini-2.5-flash"  # Stable, fast, sufficient for resume tailoring
DEFAULT_TEMPERATURE = 0.7
MAX_OUTPUT_TOKENS = 8192

# Application Configuration
APP_NAME = "Job Application Bot - AI Resume Tailorer"
APP_VERSION = "1.0.0"
DEFAULT_WINDOW_SIZE = "1400x900"

# Resume Processing
DEFAULT_RESUME_NAME = "Default Resume"
SUPPORTED_FILE_TYPES = [
    ("Text files", "*.txt"),
    ("PDF files", "*.pdf"),
    ("All files", "*.*")
]

# Date format for filenames
FILENAME_DATE_FORMAT = "%Y%m%d_%H%M%S"

# Output directories (created on startup)
RESUMES_DIR = OUTPUT_PATH / "resumes"
COVER_LETTERS_DIR = OUTPUT_PATH / "cover_letters"

# Future-proofing: Migration path to Option B
# When ready to upgrade, replace with:
# from config.settings_orm import *
# And implement Pydantic models for validation

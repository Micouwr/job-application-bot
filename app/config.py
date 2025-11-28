from __future__ import annotations

import os
from typing import Optional

# Attempt to load environment variables from a .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, proceed without it (relying on OS environment vars)
    pass


class Config:
    """
    Central configuration manager that loads settings from environment variables.
    
    This ensures that secrets (like API keys) are not hardcoded and configuration
    can be managed externally.
    """
    
    # --- API KEYS ---
    
    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        """API key for the Gemini service."""
        return os.environ.get("GEMINI_API_KEY")

    @property
    def SCRAPER_API_KEY(self) -> Optional[str]:
        """API key for the optional scraping service."""
        return os.environ.get("SCRAPER_API_KEY")

    # --- LLM CONFIGURATION ---
    
    @property
    def LLM_MODEL(self) -> str:
        """The specific LLM model name to use for analysis and tailoring."""
        return os.environ.get("LLM_MODEL", "gemini-2.5-flash") # Use a fast default

    @property
    def LLM_TEMPERATURE(self) -> float:
        """The creativity/randomness setting for the LLM (0.0 to 1.0)."""
        try:
            return float(os.environ.get("LLM_TEMPERATURE", 0.7))
        except ValueError:
            return 0.7

    # --- JOB SEARCH & SCORING CONFIGURATION ---
    
    @property
    def JOB_LOCATION(self) -> str:
        """The default location for job searches."""
        return os.environ.get("JOB_LOCATION", "Remote")
    
    @property
    def MATCH_THRESHOLD(self) -> float:
        """The minimum score for a resume to be considered a 'high match'."""
        try:
            return float(os.environ.get("MATCH_THRESHOLD", 0.80))
        except ValueError:
            return 0.80

    # --- USER INFORMATION (for dynamic resume generation, if implemented later) ---
    
    @property
    def YOUR_NAME(self) -> str:
        """The user's full name."""
        return os.environ.get("YOUR_NAME", "User Name")
    
    @property
    def YOUR_EMAIL(self) -> str:
        """The user's email address."""
        return os.environ.get("YOUR_EMAIL", "user@example.com")


# Create a single global instance for easy access throughout the app
config = Config()
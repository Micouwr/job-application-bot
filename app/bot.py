from __future__ import annotations

import logging
from typing import Dict, Any, List, Tuple

# Import all core modules
from .database import DatabaseManager
from .matcher import Matcher
from .tailor import ResumeTailor
from .scraper import JobScraper
from .config import config

logger = logging.getLogger(__name__)

class JobApplicationBot:
    """
    The main orchestrator class (Facade) for the Job Application Bot.
    It ties together the database, matcher, and tailor services.
    """

    def __init__(self):
        """Initializes all required service classes."""
        self.db_manager = DatabaseManager()
        self.matcher = Matcher(match_threshold=config.MATCH_THRESHOLD)
        # Note: ResumeTailor automatically initializes its APIClient internally
        self.tailor = ResumeTailor()
        self.scraper = JobScraper()

        logger.info("JobApplicationBot initialized with match threshold: %.2f", config.MATCH_THRESHOLD)

    def analyze_matches(self, resumes: Dict[str, str], job_text: str) -> List[Tuple[str, float]]:
        """
        Scores all provided resumes against the job description and logs the analysis.
        
        Args:
            resumes: Dictionary mapping resume name (key) to content (value).
            job_text: The full text of the job description.
            
        Returns:
            A list of (resume_name, score) tuples, sorted by score descending.
        """
        logger.info("Starting match analysis for %d resumes.", len(resumes))
        
        results = self.matcher.top_matches(resumes, job_text, top_n=len(resumes))
        
        # Log all individual match scores to history
        for resume_file, score in results:
            # We use a dummy job title here since the job object isn't formally created
            job_title = "Ad-hoc Job Analysis" 
            self.db_manager.log_analysis(job_title, resume_file, score)
        
        return results

    def tailor_application(self, resume_text: str, job_text: str, resume_file_name: str = "Uploaded Resume") -> Dict[str, Any]:
        """
        Generates a tailored resume and cover letter using the LLM and logs the result.
        
        Args:
            resume_text: The content of the resume to be tailored.
            job_text: The content of the job description.
            resume_file_name: The name used for logging this specific resume file.
            
        Returns:
            A dictionary containing the full tailored package: 
            {'resume_text': str, 'cover_letter': str, 'changes': List[str]}
        """
        logger.info("Starting application tailoring process.")
        
        # 1. Generate the tailored package using the LLM
        # This call handles the structured prompt and parsing
        tailoring_results = self.tailor.tailor_application(resume_text, job_text)
        
        # 2. Log the full result to the database (NEW STEP)
        job_title = self.scraper._guess_job_title_from_text(job_text) # Guess job title for logging
        self.db_manager.log_tailoring_result(job_title, resume_file_name, tailoring_results)
        
        logger.info("Tailoring complete and results logged.")
        
        return tailoring_results

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieves all application history."""
        return self.db_manager.get_history()

# We need a small helper function in scraper.py to guess a job title from text for logging
# I'll update scraper.py to include this helper function next, but for now, we'll
# rely on a simple placeholder guess.
# app/bot.py
from __future__ import annotations
from typing import Dict, Optional, List, Tuple
import logging

from .matcher import Matcher
from .tailor import Tailor, APIClient
from .database import Database

logger = logging.getLogger(__name__)


class JobApplicationBot:
    """
    High-level orchestrator providing a stable programmatic API for UIs.

    It composes the Matcher, Tailor, and Database modules.

    Example:
        bot = JobApplicationBot()
        analysis = bot.analyze_job("job text", {"resume1.txt": "..."})
        tailored = bot.tailor_resume("resume text", "job text")
    """

    def __init__(
        self, api_key: Optional[str] = None, db_path: Optional[str] = None
    ) -> None:
        self.matcher = Matcher()
        api_client = APIClient(api_key) if api_key else APIClient()
        self.tailor = Tailor(api_client)
        self.db = Database(db_path) if db_path else Database()

    def analyze_job(self, job_text: str, resumes: Dict[str, str]) -> List[Tuple[str, float]]:
        """
        Score a job against a set of resumes and return top matches.

        Args:
            job_text: job description text
            resumes: mapping of resume_id -> resume text

        Returns:
            list of (resume_id, score) ordered by score desc
        """
        results = self.matcher.top_matches(resumes, job_text, top_n=5)
        self.db.save_history("analyze", job_text, str(results))
        logger.info("Analyzed job; top result: %s", results[0] if results else None)
        return results

    def tailor_resume(self, resume_text: str, job_text: str) -> str:
        """
        Tailor a resume for a particular job description.

        Returns the tailored resume text and records the action in the DB.
        """
        result = self.tailor.tailor_resume(resume_text, job_text)
        self.db.save_history("tailor", job_text, result)
        logger.info("Tailored resume (len=%s)", len(result))
        return result

    def apply_to_job(self, resume_text: str, job_text: str, cover_letter: Optional[str] = None) -> Dict[str, str]:
        """
        Simulate or execute the "apply" flow.

        This placeholder method records the attempt and returns a status dict.

        Replace with the real application flow (API posting, email, ATS submission).
        """
        # TODO: integrate with actual application mechanism
        status = {"status": "queued", "message": "Application recorded locally (simulate)."}
        record = f"resume_len={len(resume_text)}; cover_letter_len={len(cover_letter or '')}"
        self.db.save_history("apply", job_text, record)
        logger.info("Apply requested; %s", status)
        return status

    def get_history(self, limit: int = 50):
        return self.db.get_history(limit)
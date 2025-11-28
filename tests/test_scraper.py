from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class JobScraper:
    """
    Utility class for generating, validating, and enriching job data objects.

    This class provides methods for creating standardized job dictionary formats
    required by the database and processing pipeline.
    """

    def __init__(self) -> None:
        pass

    def _generate_job_id(self, prefix: str = "manual_") -> str:
        """Generates a unique ID for a job listing."""
        return f"{prefix}{uuid.uuid4().hex}"

    def _guess_experience_level(self, title: str, description: str) -> str:
        """
        Guesses the experience level based on common keywords in the title and description.
        """
        title_lower = title.lower()
        description_lower = description.lower()

        if any(keyword in title_lower for keyword in ["senior", "sr.", "lead", "principal", "staff"]):
            return "Senior"
        if any(keyword in title_lower for keyword in ["junior", "jr.", "entry", "associate", "intern"]):
            return "Junior"
        if "mid-level" in description_lower or "mid-level" in title_lower:
            return "Mid"

        # Default to Mid if no clear indicators are found
        return "Mid"

    def add_manual_job(
        self,
        title: str,
        company: str,
        url: str,
        location: str = "Remote/Unknown",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Creates a structured job dictionary for a manually entered job.

        Raises:
            ValueError: If title or url are empty.
        """
        if not title or not url:
            raise ValueError("Job title and url cannot be empty")

        job_id = self._generate_job_id(prefix="manual_")
        now_iso = datetime.utcnow().isoformat()

        job = {
            "id": job_id,
            "title": title,
            "company": company,
            "url": url,
            "location": location,
            "description": description,
            "source": "manual",
            "scraped_at": now_iso,
            "status": "pending_review",  # Default starting status
            "experience_level": self._guess_experience_level(title, description),
            "match_score": 0.0,
        }
        logger.info("Created manual job ID: %s", job_id)
        return job

    def add_from_url(
        self,
        url: str,
        title: str = "Quick Import Job",
        company: str = "Unknown",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Creates a structured job dictionary for a quick URL import.
        """
        # This acts as a simple wrapper to create a job from minimal data
        job = self.add_manual_job(
            title=title,
            company=company,
            url=url,
            description=description,
        )
        job["id"] = self._generate_job_id(prefix="url_import_")
        job["source"] = "url_import"
        logger.info("Created URL import job ID: %s", job["id"])
        return job
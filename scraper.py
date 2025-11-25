"""
Job scraper module - Simplified starter version
NOTE: LinkedIn/Indeed may require authentication. Start with manual job entry.
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class JobScraper:
    """Simple job scraper - can be expanded later"""

    def __init__(self):
        self.jobs = []

    def scrape_all(
        self, keywords: List[str], location: str, max_jobs: int = 50
    ) -> List[Dict]:
        """
        Scrape jobs from all platforms

        NOTE: For initial setup, we'll use manual job entry.
        Full scraping implementation requires dealing with:
        - LinkedIn authentication
        - Rate limiting
        - Anti-bot measures

        You can add jobs manually using add_manual_job()
        """
        logger.warning(
            "Automated scraping not yet implemented. Use add_manual_job() instead."
        )
        return self.jobs

    def add_manual_job(
        self,
        title: str,
        company: str,
        url: str,
        description: str = "",
        location: str = "",
        source: str = "manual",
    ) -> Dict:
        """
        Manually add a job you found

        Usage:
            scraper = JobScraper()
            job = scraper.add_manual_job(
                title="Senior IT Architect",
                company="Tech Corp",
                url="https://company.com/jobs/123",
                description="Looking for senior architect...",
                location="Louisville, KY"
            )
        """
        if not title or not url:
            raise ValueError("Job title and url cannot be empty")

        # Generate unique ID from URL
        job_id = hashlib.md5(url.encode()).hexdigest()[:12]

        job = {
            "id": f"{source}_{job_id}",
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "requirements": self._extract_requirements(description),
            "url": url,
            "salary": None,
            "job_type": self._guess_job_type(description),
            "experience_level": self._guess_experience_level(title, description),
            "source": source,
            "scraped_at": datetime.now().isoformat(),
        }

        self.jobs.append(job)
        logger.info(f"Added manual job: {title} at {company}")

        return job

    def add_from_url(self, url: str, title: str, company: str) -> Dict:
        """
        Quick add a job from URL
        Will fetch basic info (you can enhance this later)
        """
        return self.add_manual_job(
            title=title, company=company, url=url, source="url_import"
        )

    def _extract_requirements(self, description: str) -> str:
        """Extract requirements section from description"""
        desc_lower = description.lower()
        keywords = ["requirements", "qualifications", "you have", "required skills"]

        for keyword in keywords:
            if keyword in desc_lower:
                idx = desc_lower.index(keyword)
                return description[idx : idx + 500]

        return description[:300]

    def _guess_job_type(self, text: str) -> str:
        """Guess if Remote/Hybrid/Onsite"""
        text_lower = text.lower()
        if "remote" in text_lower or "work from home" in text_lower:
            return "Remote"
        elif "hybrid" in text_lower:
            return "Hybrid"
        return "Onsite"

    def _guess_experience_level(self, title: str, description: str) -> str:
        """Guess experience level"""
        text = f"{title} {description}".lower()
        if "senior" in text or "sr." in text or "lead" in text:
            return "Senior"
        elif "junior" in text or "entry" in text:
            return "Junior"
        return "Mid"


def demo_scraper():
    """Demo function showing how to add jobs manually"""
    scraper = JobScraper()

    # Example 1: Add a job you found on LinkedIn
    job1 = scraper.add_manual_job(
        title="Senior IT Infrastructure Architect",
        company="Example Tech Corp",
        url="https://www.linkedin.com/jobs/view/123456789",
        description="""
        We're looking for a Senior IT Infrastructure Architect with 10+ years experience.

        Requirements:
        - AWS Cloud experience
        - Help desk management
        - Network security
        - AI/ML knowledge preferred

        This is a remote position based in Louisville, KY area.
        """,
        location="Louisville, KY (Remote)",
        source="linkedin",
    )

    # Example 2: Quick add from URL
    job2 = scraper.add_from_url(
        url="https://www.indeed.com/viewjob?jk=abc123",
        title="Help Desk Manager",
        company="Enterprise Solutions",
    )

    print(f"Added {len(scraper.jobs)} jobs")
    return scraper.jobs


if __name__ == "__main__":
    # Test the scraper
    jobs = demo_scraper()
    for job in jobs:
        print(f"- {job['title']} at {job['company']}")

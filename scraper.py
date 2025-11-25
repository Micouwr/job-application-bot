"""
Job scraper module - Secure job ID generation and manual entry
NOTE: LinkedIn/Indeed require authentication. Use manual entry for now.
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class JobScraper:
    """Simple job scraper with secure ID generation and duplicate detection"""

    def __init__(self):
        self.jobs = []

    def add_manual_job(
        self,
        title: str,
        company: str,
        url: str,
        description: str = "",
        location: str = "",
        source: str = "manual",
    ) -> Optional[Dict]:
        """
        Manually add a job you found with secure ID generation
        
        Args:
            title: Job title (required)
            company: Company name (required)
            url: Job URL (required for duplicate detection)
            description: Full job description (required)
            location: Job location
            source: Source platform (manual, linkedin, indeed)
            
        Returns:
            Job dictionary or None if duplicate/already exists
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if not title or not title.strip():
            raise ValueError("Job title cannot be empty")
        
        if not company or not company.strip():
            company = "Unknown"
            logger.warning("Company name not provided, using 'Unknown'")
        
        if not url:
            # Generate URL from job details if not provided
            url = f"manual://{source}/{hashlib.sha256(title.encode()).hexdigest()[:16]}"
            logger.warning(f"No URL provided, generating: {url}")
        
        if not description or not description.strip():
            raise ValueError("Job description cannot be empty")

        # Generate secure job ID
        # Use SHA-256 (not broken like MD5) and include full source
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
        job_id = f"{source}_{url_hash[:16]}"  # 16 chars = 64^16 possibilities

        # Check for duplicates
        # This is critical - prevent duplicate job entries
        existing_job = next((j for j in self.jobs if j["url"] == url), None)
        if existing_job:
            logger.warning(f"Job already exists in scraper cache: {url}")
            return None

        # Build job dictionary
        job = {
            "id": job_id,
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "description": description.strip(),
            "requirements": self._extract_requirements(description),
            "url": url,
            "salary": None,  # Could be extracted from description
            "job_type": self._guess_job_type(description),
            "experience_level": self._guess_experience_level(title, description),
            "source": source,
            "scraped_at": datetime.now().isoformat(),
        }

        self.jobs.append(job)
        logger.info(f"Added manual job: {job['title']} at {job['company']} (ID: {job_id})")
        
        return job

    def add_from_url(self, url: str, title: str, company: str) -> Optional[Dict]:
        """
        Quick add a job from URL with minimal information
        
        Args:
            url: Job posting URL
            title: Job title
            company: Company name
            
        Returns:
            Job dictionary or None if duplicate
        """
        return self.add_manual_job(
            title=title,
            company=company,
            url=url,
            description=f"Job added from URL: {url}",
            source="url_import"
        )

    def _extract_requirements(self, description: str) -> str:
        """Extract requirements section from description"""
        if not description:
            return ""
        
        desc_lower = description.lower()
        keywords = ["requirements", "qualifications", "you have", "required skills", "what you need"]
        
        for keyword in keywords:
            if keyword in desc_lower:
                try:
                    idx = desc_lower.index(keyword)
                    # Return next 500 chars
                    return description[idx:idx+500].strip()
                except ValueError:
                    continue
        
        # Fallback: return first 300 chars
        return description[:300].strip()

    def _guess_job_type(self, text: str) -> str:
        """Guess if Remote/Hybrid/Onsite from text"""
        if not text:
            return "Unknown"
        
        text_lower = text.lower()
        if "remote" in text_lower or "work from home" in text_lower:
            return "Remote"
        elif "hybrid" in text_lower:
            return "Hybrid"
        return "Onsite"

    def _guess_experience_level(self, title: str, description: str) -> str:
        """Guess experience level from title and description"""
        if not title and not description:
            return "Unknown"
        
        text = f"{title} {description}".lower()
        
        senior_terms = ["senior", "sr.", "lead", "principal", "staff", "architect", "director"]
        junior_terms = ["junior", "jr.", "entry", "associate"]
        
        if any(term in text for term in senior_terms):
            return "Senior"
        elif any(term in text for term in junior_terms):
            return "Junior"
        
        return "Mid"

# Demo usage
def demo_scraper():
    """Demo function showing how to add jobs manually"""
    scraper = JobScraper()

    # Example 1: Add a job you found on LinkedIn
    job = scraper.add_manual_job(
        title="Senior IT Infrastructure Architect",
        company="Example Tech Corp",
        url="https://www.linkedin.com/jobs/view/123456789",
        description="""
We're looking for a Senior IT Infrastructure Architect with 10+ years of experience.

Requirements:
- AWS Cloud experience
- Help desk management
- Network security
- AI/ML knowledge preferred

This is a remote position based in the Louisville, KY area.
        """,
        location="Louisville, KY",
        source="linkedin",
    )
    
    if job:
        print(f"✓ Added: {job['title']} at {job['company']}")
        print(f"  ID: {job['id']}")
        print(f"  URL: {job['url']}")
    
    # Example 2: Demonstrate duplicate detection
    duplicate = scraper.add_manual_job(
        title="Different Title",  # Same URL = duplicate
        company="Different Company",
        url="https://www.linkedin.com/jobs/view/123456789",
        description="This should be rejected as duplicate",
    )
    
    if duplicate is None:
        print("✓ Duplicate detection working correctly")

    return scraper.jobs

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        jobs = demo_scraper()
        print(f"\nTotal jobs in scraper: {len(jobs)}")
        for j in jobs:
            print(f"- {j['title']} at {j['company']} (ID: {j['id']})")
    except Exception as e:
        logger.error(f"Demo failed: {e}")

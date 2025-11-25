"""
Job scraper module - Enhanced with duplicate detection and URL normalization.
Note: Automated scraping for LinkedIn/Indeed requires authentication and has rate limits.
Consider using official APIs or manual entry for reliability.
"""

import logging
import hashlib
import urllib.parse
from datetime import datetime
from typing import Dict, List, Any, Optional

from config.settings import Config

logger = logging.getLogger(__name__)

class JobScraper:
    """Enhanced job scraper with duplicate detection and validation."""
    
    def __init__(self, db=None):
        """
        Initialize scraper with optional database for duplicate checking.
        
        Args:
            db: JobDatabase instance for duplicate checking
        """
        self.jobs: List[Dict[str, Any]] = []
        self.db = db
        logger.info("✓ JobScraper initialized")
    
    def add_manual_job(
        self,
        title: str,
        company: str,
        url: str,
        description: str = "",
        location: str = "",
        source: str = "manual",
    ) -> Optional[Dict[str, Any]]:
        """
        Manually add a job with validation and duplicate detection.
        Returns job dict or None if duplicate/invalid.
        """
        try:
            # Validate inputs
            if not title or not isinstance(title, str) or len(title.strip()) == 0:
                logger.error("Invalid job title")
                return None
            
            if len(title) > 200:
                logger.error(f"Job title too long: {len(title)} chars")
                return None
            
            # Normalize URL
            clean_url = self._normalize_url(url) if url else ""
            
            # Generate unique job ID
            job_id = self._generate_job_id(title, company, clean_url, source)
            
            # Check for duplicates
            if self._is_duplicate(job_id):
                logger.warning(f"Duplicate job detected: {title} at {company}")
                return None
            
            # Extract structured data from description
            requirements = self._extract_requirements(description)
            job_type = self._guess_job_type(description)
            experience_level = self._guess_experience_level(title, description)
            
            # Build job dictionary
            job = {
                "id": job_id,
                "title": title.strip(),
                "company": company.strip(),
                "location": location.strip() or Config.JOB_LOCATION,
                "description": description.strip(),
                "requirements": requirements,
                "url": clean_url,
                "salary": None,
                "job_type": job_type,
                "experience_level": experience_level,
                "source": source,
                "scraped_at": datetime.now().isoformat(),
                "raw_data": {},  # Placeholder for future scraping data
            }
            
            self.jobs.append(job)
            logger.info(f"Added manual job: {title[:50]}... at {company}")
            
            return job
            
        except Exception as e:
            logger.error(f"Error adding manual job: {e}")
            return None
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing tracking parameters and fragments"""
        try:
            if not url:
                return ""
            
            # Ensure URL has scheme
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            parsed = urllib.parse.urlparse(url)
            
            # Remove common tracking parameters
            query_params = urllib.parse.parse_qs(parsed.query)
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid'}
            clean_params = {k: v for k, v in query_params.items() if k.lower() not in tracking_params}
            
            # Reconstruct URL without tracking
            clean_query = urllib.parse.urlencode(clean_params, doseq=True)
            normalized = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc.lower(),  # Normalize domain to lowercase
                parsed.path,
                parsed.params,
                clean_query,
                ''  # Remove fragment
            ))
            
            return normalized
            
        except Exception as e:
            logger.warning(f"URL normalization failed for {url}: {e}")
            return url
    
    def _generate_job_id(self, title: str, company: str, url: str, source: str) -> str:
        """Generate unique, deterministic job ID"""
        try:
            # Use URL + title as primary identifier
            if url:
                id_string = f"{url}_{title}"
            else:
                # Fallback if no URL
                id_string = f"{source}_{company}_{title}_{datetime.now().date()}"
            
            # Use SHA256 for better collision resistance
            job_hash = hashlib.sha256(id_string.encode('utf-8')).hexdigest()
            
            # Return source + first 16 chars of hash
            return f"{source}_{job_hash[:16]}"
            
        except Exception as e:
            logger.error(f"Error generating job ID: {e}")
            # Fallback ID
            return f"error_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12]}"
    
    def _is_duplicate(self, job_id: str) -> bool:
        """Check if job already exists in database or local list"""
        try:
            # Check in local list
            if any(job["id"] == job_id for job in self.jobs):
                return True
            
            # Check in database if available
            if self.db and hasattr(self.db, 'job_exists'):
                return self.db.job_exists(job_id)
            
            return False
            
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
            return False
    
    def _extract_requirements(self, description: str) -> str:
        """Extract requirements section from job description"""
        try:
            if not description:
                return ""
            
            desc_lower = description.lower()
            keywords = [
                "requirements",
                "qualifications",
                "required skills",
                "what you need",
                "you have",
                "must have"
            ]
            
            # Find the earliest requirements section
            min_idx = len(description)
            found_keyword = ""
            
            for keyword in keywords:
                idx = desc_lower.find(keyword)
                if idx != -1 and idx < min_idx:
                    min_idx = idx
                    found_keyword = keyword
            
            if found_keyword:
                # Return from keyword to end or next major section
                req_section = description[min_idx:min_idx + 1500]
                # Try to find end of section (next heading)
                lines = req_section.split('\n')
                requirements = []
                for line in lines[:20]:  # Max 20 lines
                    if any(heading in line.lower() for heading in ['responsibilities', 'benefits', 'about us']):
                        break
                    requirements.append(line)
                return '\n'.join(requirements)
            
            # Fallback: return beginning of description
            return description[:800]
            
        except Exception as e:
            logger.warning(f"Error extracting requirements: {e}")
            return description[:500]
    
    def _guess_job_type(self, text: str) -> str:
        """Guess if Remote/Hybrid/Onsite from text"""
        try:
            if not text:
                return "Unknown"
            
            text_lower = text.lower()
            
            # Check for remote indicators
            remote_indicators = ['remote', 'work from home', 'wfh', 'fully remote']
            if any(indicator in text_lower for indicator in remote_indicators):
                # Check for hybrid
                if 'hybrid' in text_lower:
                    return 'Hybrid'
                return 'Remote'
            
            # Check for hybrid explicitly
            if 'hybrid' in text_lower:
                return 'Hybrid'
            
            return 'On-site'
            
        except Exception as e:
            logger.warning(f"Error guessing job type: {e}")
            return "Unknown"
    
    def _guess_experience_level(self, title: str, description: str) -> str:
        """Guess experience level from title and description"""
        try:
            text = f"{title} {description}".lower()
            
            # Senior indicators
            senior_indicators = [
                'senior', 'sr.', 'lead', 'principal', 'architect', 'manager',
                'director', 'head of', 'vp', 'vice president', '10+ years',
                '15+ years', '20+ years'
            ]
            
            # Junior indicators
            junior_indicators = [
                'junior', 'jr.', 'entry level', 'entry-level', 'associate',
                '0-2 years', '1 year', '2 years', 'recent graduate'
            ]
            
            if any(indicator in text for indicator in senior_indicators):
                return 'Senior'
            elif any(indicator in text for indicator in junior_indicators):
                return 'Junior'
            else:
                return 'Mid-level'
                
        except Exception as e:
            logger.warning(f"Error guessing experience level: {e}")
            return "Unknown"
    
    def add_from_url(self, url: str, title: str, company: str) -> Optional[Dict[str, Any]]:
        """
        Quick-add a job from URL with basic info.
        Will fetch details in future implementation.
        """
        try:
            if not url or not title or not company:
                logger.error("URL, title, and company are required")
                return None
            
            return self.add_manual_job(
                title=title,
                company=company,
                url=url,
                description="",  # To be filled by scraper later
                source="url_import"
            )
        except Exception as e:
            logger.error(f"Error adding from URL: {e}")
            return None
    
    def scrape_all(
        self,
        keywords: List[str],
        location: str,
        max_jobs: int = 50,
        sources: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape jobs from multiple platforms.
        NOTE: This is a placeholder. Full implementation requires:
        - API keys (LinkedIn, Indeed)
        - Rate limiting and backoff
        - Anti-bot detection handling
        - Captcha solving (if needed)
        
        Recommended: Use manual entry or official APIs.
        """
        logger.warning(
            "Automated scraping not fully implemented. "
            "Consider using manual entry or official job board APIs. "
            "LinkedIn and Indeed have strong anti-bot measures."
        )
        
        # Placeholder for future implementation
        # Would include: LinkedInAPI, IndeedAPI, DiceAPI, MonsterAPI classes
        
        return self.jobs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics"""
        return {
            "total_jobs": len(self.jobs),
            "sources": list(set(job.get("source", "unknown") for job in self.jobs)),
            "companies": list(set(job.get("company", "unknown") for job in self.jobs)),
        }

def demo_scraper():
    """Demo the scraper with sample jobs"""
    logging.basicConfig(level=logging.INFO)
    
    scraper = JobScraper()
    
    # Example 1: Add a real job
    job1 = scraper.add_manual_job(
        title="Senior IT Infrastructure Architect",
        company="Amazon Web Services",
        url="https://www.amazon.jobs/en/jobs/123456",
        description="""
        AWS is seeking a Senior IT Infrastructure Architect to design and implement
        cloud-native infrastructure solutions. You will lead a team of engineers
        and work with enterprise clients on their digital transformation.
        
        Requirements:
        - 10+ years IT infrastructure experience
        - AWS Certified Solutions Architect
        - Strong Python and automation skills
        - Help desk/service desk leadership
        - Knowledge of AI/ML infrastructure
        
        Preferred:
        - ISO/IEC 42001 familiarity
        - Network security expertise
        - Cisco Meraki experience
        
        This is a remote position.
        """,
        location="Remote",
        source="amazon"
    )
    
    # Example 2: Add another job
    job2 = scraper.add_manual_job(
        title="Help Desk Manager",
        company="Enterprise Solutions Inc",
        url="https://example.com/jobs/789",
        description="""
        Lead our 15-person help desk team supporting 2000+ users.
        Must have proven leadership and training development experience.
        
        Key Responsibilities:
        - Manage daily help desk operations
        - Develop training programs
        - Optimize SLA performance
        
        Required: 5+ years help desk experience, team leadership.
        """,
        location="Louisville, KY"
    )
    
    if job1:
        print(f"\n✓ Added job: {job1['title']}")
    if job2:
        print(f"✓ Added job: {job2['title']}")
    
    stats = scraper.get_stats()
    print(f"\nScraper Stats: {stats}")

if __name__ == "__main__":
    demo_scraper()

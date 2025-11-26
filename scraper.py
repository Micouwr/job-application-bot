"""
Job scraper module - Enhanced with job board integrations, URL parsing, and smart deduplication.
"""

import hashlib
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class URLValidator:
    """✅ QoL: Validate and normalize URLs"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for deduplication"""
        if not url:
            return ""
        
        parsed = urlparse(url.lower())
        # Remove query parameters that don't affect job content
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain for job board detection"""
        if not url:
            return ""
        return urlparse(url).netloc.lower()


class JobBoardIntegration:
    """
    ✅ QoL: Integration class for various job boards using ScraperAPI
    """
    
    def __init__(self, scraper_api_key: Optional[str] = None):
        self.scraper_api_key = scraper_api_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        # Job board detection patterns
        self.job_board_patterns = {
            "linkedin.com": self._parse_linkedin_job,
            "indeed.com": self._parse_indeed_job,
            "glassdoor.com": self._parse_glassdoor_job,
        }
        
        logger.info(f"✓ JobBoardIntegration initialized")

    def scrape_all(self, keywords: List[str], location: str, max_jobs: int = 50) -> List[Dict[str, Any]]:
        """
        Scrape jobs from multiple job boards.
        
        For now, this is a placeholder. Full implementation would:
        1. Use ScraperAPI to bypass anti-bot measures
        2. Parse each job board's HTML structure
        3. Handle pagination and rate limiting
        """
        if not self.scraper_api_key:
            logger.warning("No ScraperAPI key provided. Skipping automated scraping.")
            return []
        
        logger.info(f"Starting scrape for keywords: {keywords} in {location}")
        jobs = []
        
        # Placeholder for actual scraping logic
        # TODO: Implement actual scraping with ScraperAPI
        
        return jobs

    def add_manual_job(
        self,
        title: str,
        company: str,
        url: str,
        description: str = "",
        location: str = "",
        source: str = "manual",
    ) -> Dict[str, Any]:
        """
        ✅ Fix: Enhanced manual job addition with validation and deduplication
        """
        # Validate URL
        if url and not URLValidator.is_valid_url(url):
            logger.warning(f"Invalid URL format: {url}")
            url = ""
        
        # Normalize URL for consistent ID generation
        normalized_url = URLValidator.normalize_url(url) if url else f"manual_{hashlib.md5(title.encode()).hexdigest()[:12]}"
        
        # Generate unique ID
        job_id = hashlib.md5(normalized_url.encode()).hexdigest()[:12]
        job_id = f"{source}_{job_id}"
        
        # ✅ Fix: Improved job type detection with correct priority
        job_type = self._guess_job_type(description)
        
        # ✅ Fix: Enhanced experience level detection
        exp_level = self._guess_experience_level(title, description)
        
        job = {
            "id": job_id,
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip() or "Unknown",
            "description": description.strip(),
            "requirements": self._extract_requirements(description),
            "url": url,
            "salary": self._extract_salary(description),
            "job_type": job_type,
            "experience_level": exp_level,
            "source": source,
            "scraped_at": datetime.now().isoformat(),
            "tags": self._auto_tag_job(description),  # ✅ QoL: Auto-tagging
        }

        logger.info(f"Added manual job: {title} at {company} (ID: {job_id})")
        return job

    def _extract_requirements(self, description: str) -> str:
        """  Extract requirements section from description """
        if not description:
            return ""
        
        desc_lower = description.lower()
        keywords = ["requirements", "qualifications", "you have", "required skills", "what you need"]
        
        for keyword in keywords:
            if keyword in desc_lower:
                try:
                    idx = desc_lower.index(keyword)
                    # Extract up to 1000 chars or until next major section
                    section = description[idx:idx + 1000]
                    # Stop at next common section header
                    next_section = section.lower().find("\n\n", 100)
                    if next_section > 0:
                        return section[:next_section]
                    return section
                except ValueError:
                    continue
        
        return description[:500]

    def _guess_job_type(self, text: str) -> str:
        """
        ✅ Fix: Improved job type detection with correct priority
        Handles cases like "hybrid remote" correctly
        """
        if not text:
            return "Onsite"
        
        text_lower = text.lower()
        
        # Check for hybrid first (since it might contain "remote")
        if "hybrid" in text_lower:
            return "Hybrid"
        
        # Then check for remote
        if "remote" in text_lower or "work from home" in text_lower:
            return "Remote"
        
        return "Onsite"

    def _guess_experience_level(self, title: str, description: str) -> str:
        """
        ✅ Fix: Enhanced experience level detection with multiple indicators
        """
        if not title and not description:
            return "Unknown"
        
        combined = f"{title} {description}".lower()
        
        # Senior indicators
        senior_indicators = [
            "senior", "sr.", "sr ", "lead", "principal", "staff", "architect",
            "manager", "director", "head of", "vp ", "vice president"
        ]
        
        # Junior indicators
        junior_indicators = [
            "junior", "jr.", "jr ", "entry", "associate", "intern", "trainee",
            "junior level", "early career"
        ]
        
        # Mid indicators
        mid_indicators = ["mid", "intermediate", "mid-level", "ii", "2", "level 2"]
        
        # Check senior first (most specific)
        if any(indicator in combined for indicator in senior_indicators):
            return "Senior"
        
        # Check junior
        if any(indicator in combined for indicator in junior_indicators):
            return "Junior"
        
        # Check mid
        if any(indicator in combined for indicator in mid_indicators):
            return "Mid"
        
        # Default based on title complexity
        if len(title.split()) > 4 and any(word in title.lower() for word in ['cloud', 'architect', 'manager']):
            return "Senior"
        
        return "Unknown"

    def _extract_salary(self, text: str) -> Optional[str]:
        """ ✅ QoL: Extract salary information using regex patterns """
        if not text:
            return None
        
        text = text.replace(",", "")
        
        # Common salary patterns
        patterns = [
            r'\$[\d,]+\s*(?:k|K)?\s*-\s*\$[\d,]+\s*(?:k|K)?',  # $50k - $80k
            r'\$[\d,]+\s*(?:k|K)?\s*(?:per year|\/year|\/yr|annual|annually)?',  # $50000 per year
            r'(?:salary|compensation|pay):\s*\$[\d,]+',  # Salary: $50000
            r'\d+\s*(?:k|K)\s*-\s*\d+\s*(?:k|K)',  # 50k-80k
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None

    def _auto_tag_job(self, description: str) -> List[str]:
        """
        ✅ QoL: Auto-tag jobs based on content
        """
        tags = []
        desc_lower = description.lower()
        
        # Remote work tags
        if "remote" in desc_lower:
            tags.append("remote")
        if "hybrid" in desc_lower:
            tags.append("hybrid")
        
        # Tech tags
        tech_keywords = {
            "python": "python",
            "aws": "aws",
            "azure": "azure",
            "docker": "docker",
            "kubernetes": "kubernetes",
            "ansible": "ansible",
            "terraform": "terraform",
        }
        
        for keyword, tag in tech_keywords.items():
            if keyword in desc_lower:
                tags.append(tag)
        
        # Experience level tags
        if "entry level" in desc_lower or "junior" in desc_lower:
            tags.append("entry-level")
        elif "senior" in desc_lower or "sr." in desc_lower:
            tags.append("senior")
        
        # Visa sponsorship
        if "visa sponsorship" in desc_lower or "sponsorship available" in desc_lower:
            tags.append("visa-sponsorship")
        
        return list(set(tags))  # Remove duplicates

    def _parse_linkedin_job(self, url: str) -> Optional[Dict[str, Any]]:
        """ ✅ QoL: Parse LinkedIn job page (placeholder) """
        try:
            # TODO: Implement LinkedIn parsing with ScraperAPI
            # This would handle LinkedIn's dynamic content
            logger.info(f"Parsing LinkedIn job: {url}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse LinkedIn job: {e}")
            return None

    def _parse_indeed_job(self, url: str) -> Optional[Dict[str, Any]]:
        """ ✅ QoL: Parse Indeed job page (placeholder) """
        try:
            # TODO: Implement Indeed parsing
            logger.info(f"Parsing Indeed job: {url}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse Indeed job: {e}")
            return None

    def _parse_glassdoor_job(self, url: str) -> Optional[Dict[str, Any]]:
        """✅ QoL: Parse Glassdoor job page (placeholder)"""
        try:
            # TODO: Implement Glassdoor parsing
            logger.info(f"Parsing Glassdoor job: {url}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse Glassdoor job: {e}")
            return None


class JobScraper:
    """ Legacy scraper class for backward compatibility """
    
    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self.integrations = JobBoardIntegration()
        logger.info("✓ JobScraper initialized (legacy mode)")

    def scrape_all(
        self, keywords: List[str], location: str, max_jobs: int = 50
    ) -> List[Dict[str, Any]]:
        """
        ⚠️  Deprecated: Use JobBoardIntegration instead
        """
        logger.warning(
            "JobScraper.scrape_all() is deprecated. Use JobBoardIntegration.scrape_all() instead."
        )
        return self.integrations.scrape_all(keywords, location, max_jobs)

    def add_manual_job(
        self,
        title: str,
        company: str,
        url: str = "",
        description: str = "",
        location: str = "",
        source: str = "manual",
    ) -> Dict[str, Any]:
        """Delegate to JobBoardIntegration"""
        return self.integrations.add_manual_job(title, company, url, description, location, source)

    def add_from_url(self, url: str, title: str, company: str) -> Dict[str, Any]:
        """
        ✅ QoL: Quick add a job from URL with automatic fetching
        """
        if not url:
            raise ValueError("URL is required")
        
        # Try to fetch job details from URL
        job_data = self._fetch_job_from_url(url)
        
        if job_data:
            logger.info(f"✓ Automatically fetched job details from {url}")
            return self.add_manual_job(
                title=job_data.get("title", title),
                company=job_data.get("company", company),
                url=url,
                description=job_data.get("description", ""),
                location=job_data.get("location", ""),
                source="url_import"
            )
        else:
            # Fallback to manual entry
            logger.warning(f"Could not fetch job details from {url}, using manual data")
            return self.add_manual_job(title=title, company=company, url=url, source="url_import")

    def _fetch_job_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """ ✅ QoL: Fetch job details from URL using BeautifulSoup """
        try:
            # Detect job board
            domain = URLValidator.extract_domain(url)
            
            # Use board-specific parser if available
            if "linkedin.com" in domain:
                return self.integrations._parse_linkedin_job(url)
            elif "indeed.com" in domain:
                return self.integrations._parse_indeed_job(url)
            elif "glassdoor.com" in domain:
                return self.integrations._parse_glassdoor_job(url)
            
            # Generic fallback parser
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find title
            title = None
            title_tags = ['h1', 'h2', 'title']
            for tag in title_tags:
                title_elem = soup.find(tag)
                if title_elem and 'job' in title_elem.get_text().lower():
                    title = title_elem.get_text().strip()
                    break
            
            # Try to find description
            description = ""
            desc_selectors = ['[class*="description"]', '[class*="job-description"]', 
                            '#job-description', '.job-description']
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(separator='\n').strip()
                    break
            
            return {
                "title": title,
                "description": description,
                "url": url
            }
            
        except Exception as e:
            logger.warning(f"Could not fetch job from URL {url}: {e}")
            return None


def demo_scraper() -> List[Dict[str, Any]]:
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
    
    # Example 2: Quick add from URL (will try to auto-fetch)
    job2 = scraper.add_from_url(
        url="https://www.indeed.com/viewjob?jk=abc123",
        title="Help Desk Manager",
        company="Enterprise Solutions",
    )
    
    logger.info(f"Demo: Added {len(scraper.jobs)} jobs")
    return scraper.jobs


if __name__ == "__main__":
    # Test the scraper
    jobs = demo_scraper()
    for job in jobs:
        print(f"- {job['title']} at {job['company']}")
        print(f"  ID: {job['id']}")
        print(f"  Type: {job['job_type']}")
        print(f"  Level: {job['experience_level']}")
        print(f"  Tags: {job.get('tags', [])}")

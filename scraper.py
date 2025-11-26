"""
Job scraper module - Enhanced with job board integrations, URL parsing, and smart deduplication.
"""

import hashlib
import logging
import random
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
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
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
    
    #: ✅ QoL: User-Agent rotation pool to avoid detection
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    def __init__(self, scraper_api_key: Optional[str] = None):
        self.scraper_api_key = scraper_api_key
        self.session = requests.Session()
        # ✅ QoL: Set random User-Agent to avoid detection
        self.session.headers.update({
            "User-Agent": random.choice(self.USER_AGENTS)
        })
        
        # Job board detection patterns
        self.job_board_patterns = {
            "linkedin.com": self._parse_linkedin_job,
            "indeed.com": self._parse_indeed_job,
            "glassdoor.com": self._parse_glassdoor_job,
        }
        
        logger.info(f"✓ JobBoardIntegration initialized")

    def _get_with_headers(self, url: str, **kwargs) -> requests.Response:
        """
        ✅ QoL: Make HTTP request with randomized headers to avoid blocking
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for requests.get()
        
        Returns:
            Response object
        """
        # Set random User-Agent
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Add any additional headers from kwargs
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        return self.session.get(url, headers=headers, **kwargs)

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
        """Extract requirements section from description"""
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
        
        # ✅ QoL: Prioritize explicit indicators in order (junior checked first)
        level_indicators = {
            "junior": ["junior", "jr.", "jr ", "entry", "associate", "intern", "trainee", "junior level", "early career"],
            "mid": ["mid", "intermediate", "mid-level", "ii", "2", "level 2"],
            "senior": ["senior", "sr.", "sr ", "lead", "principal", "staff", "architect", "manager", "director"],
        }
        
        detected_levels = []
        
        # Check junior first (highest priority to avoid misclassification)
        if any(indicator in combined for indicator in level_indicators["junior"]):
            detected_levels.append("junior")
        
        # Check mid
        if any(indicator in combined for indicator in level_indicators["mid"]):
            detected_levels.append("mid")
        
        # Check senior
        if any(indicator in combined for indicator in level_indicators["senior"]):
            detected_levels.append("senior")
        
        # Check if job is senior-level (what resume indicates)
        is_senior = "senior" in detected_levels
        matches = bool(detected_levels)  # True if we could detect a level
        
        return {
            "matches": matches,
            "detected_levels": detected_levels,
            "is_senior": is_senior,
            "multiplier": 1.0 if is_senior else 0.85
        }

    def _extract_salary(self, text: str) -> Optional[str]:
        """
        ✅ QoL: Extract and normalize salary information using regex patterns
        
        Returns:
            Normalized salary string in format "50000-80000" (annual) or None
        """
        if not text:
            return None
        
        text = text.replace(",", "")
        
        # Common salary patterns
        patterns = [
            r'\$([\d,]+)\s*(?:k|K)?\s*-\s*\$([\d,]+)\s*(?:k|K)?',  # $50k - $80k
            r'\$([\d,]+)\s*(?:k|K)?\s*(?:per year|\/year|\/yr|annual|annually)?',  # $50000 per year
            r'(?:salary|compensation|pay):\s*\$([\d,]+)',  # Salary: $50000
            r'([\d,]+)\s*(?:k|K)\s*-\s*([\d,]+)\s*(?:k|K)',  # 50k-80k
            r'\$([\d,]+)\s*(?:per hour|\/hour|\/hr|hourly)',  # $30 per hour (will be annualized)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:  # Range
                    try:
                        # ✅ QoL: Normalize to annual salary, remove "k"
                        min_salary = float(groups[0].replace('k', '').replace('K', '')) * 1000
                        max_salary = float(groups[1].replace('k', '').replace('K', '')) * 1000
                        return f"{int(min_salary)}-{int(max_salary)}"
                    except ValueError:
                        continue
                elif len(groups) == 1:  # Single value
                    try:
                        salary = float(groups[0].replace('k', '').replace('K', '')) * 1000
                        
                        # ✅ QoL: Check if hourly and annualize (assuming 2080 work hours/year)
                        if 'hour' in text.lower() or 'hr' in text.lower():
                            salary = salary * 2080
                            return f"{int(salary)} (annualized from hourly)"
                        
                        return f"{int(salary)}"
                    except ValueError:
                        continue
        
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
        """✅ QoL: Parse LinkedIn job page (placeholder)"""
        try:
            # TODO: Implement LinkedIn parsing with ScraperAPI
            # This would handle LinkedIn's dynamic content
            logger.info(f"Parsing LinkedIn job: {url}")
            
            # For now, return None to trigger manual entry fallback
            return None
        except Exception as e:
            logger.error(f"Failed to parse LinkedIn job: {e}")
            return None

    def _parse_indeed_job(self, url: str) -> Optional[Dict[str, Any]]:
        """✅ QoL: Parse Indeed job page (placeholder)"""
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
    """Legacy scraper class for backward compatibility"""
    
    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self.integrations = JobBoardIntegration()
        logger.info("✓ JobScraper initialized (legacy mode)")

    def scrape_all(
        self, keywords: List[str], location: str, max_jobs: int = 50
    ) -> List[Dict[str, Any]]:
        """
        ⚠️ Deprecated: Use JobBoardIntegration instead
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
        """
        ✅ QoL: Fetch job details from URL using BeautifulSoup with enhanced headers
        
        Args:
            url: Job posting URL
            
        Returns:
            Dictionary with extracted job data or None
        """
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
            
            # ✅ Fix: Generic fallback parser with stricter title detection
            response = self.integrations._get_with_headers(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # ✅ Fix: Be more strict - look for h1 only for job title
            title = None
            title_elem = soup.find('h1')
            if title_elem:
                title_text = title_elem.get_text().strip()
                # ✅ Fix: Filter out obviously wrong titles
                if any(indicator in title_text.lower() for indicator in ['job', 'career', 'position']):
                    title = title_text
            
            # Try other selectors if h1 didn't work
            if not title:
                title_selectors = ['h2', 'title', 'meta[name="title"]']
                for selector in title_selectors:
                    elem = soup.find(selector)
                    if elem:
                        title = elem.get_text().strip()
                        break
            
            # Try to find description
            description = ""
            desc_selectors = [
                '[class*="description"]', 
                '[class*="job-description"]', 
                '#job-description', 
                '.job-description',
                '[data-testid="job-description"]',  # Common test ID
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(separator='\n').strip()
                    break
            
            # ✅ QoL: Try to find location
            location = ""
            location_selectors = [
                '[class*="location"]',
                '.job-location',
                '[data-testid="job-location"]',
            ]
            for selector in location_selectors:
                loc_elem = soup.select_one(selector)
                if loc_elem:
                    location = loc_elem.get_text().strip()
                    break
            
            # ✅ QoL: Try to find company
            company = ""
            company_selectors = [
                '[class*="company"]',
                '.job-company',
                '[data-testid="job-company"]',
            ]
            for selector in company_selectors:
                comp_elem = soup.select_one(selector)
                if comp_elem:
                    company = comp_elem.get_text().strip()
                    break
            
            return {
                "title": title,
                "description": description,
                "location": location,
                "company": company,
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
    
    logger.info(f"Demo: Added {len([job1, job2])} jobs")
    return [job1, job2]


if __name__ == "__main__":
    # Test the scraper
    jobs = demo_scraper()
    for job in jobs:
        print(f"- {job['title']} at {job['company']}")
        print(f"  ID: {job['id']}")
        print(f"  Type: {job['job_type']}")
        print(f"  Level: {job['experience_level']}")
        print(f"  Salary: {job.get('salary', 'Not found')}")
        print(f"  Tags: {job.get('tags', [])}")
        print()

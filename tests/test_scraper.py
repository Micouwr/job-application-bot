"""
Tests for the JobScraper class.
"""

from scraper import JobScraper


def test_add_manual_job():
    """Tests that a job can be added manually."""
    scraper = JobScraper()
    job = scraper.add_manual_job(
        title="Software Engineer",
        company="Tech Corp",
        url="https://example.com",
        description="Test description",
    )
    assert job["title"] == "Software Engineer"
    assert job["company"] == "Tech Corp"
    assert job["url"] == "https://example.com"


def test_extract_requirements():
    """Tests that requirements can be extracted from a job description."""
    scraper = JobScraper()
    description = "Requirements: Python, AWS"
    requirements = scraper._extract_requirements(description)
    assert "Python" in requirements
    assert "AWS" in requirements


def test_guess_job_type():
    """Tests that the job type can be guessed from a job description."""
    scraper = JobScraper()
    assert scraper._guess_job_type("remote") == "Remote"
    assert scraper._guess_job_type("hybrid") == "Hybrid"
    assert scraper._guess_job_type("onsite") == "Onsite"


def test_guess_experience_level():
    """Tests that the experience level can be guessed from a job title."""
    scraper = JobScraper()
    assert scraper._guess_experience_level("Senior Software Engineer", "") == "Senior"
    assert scraper._guess_experience_level("Junior Software Engineer", "") == "Junior"
    assert scraper._guess_experience_level("Software Engineer", "") == "Mid"

import pytest

from scraper import JobScraper


@pytest.fixture
def scraper():
    return JobScraper()


def test_add_manual_job_generates_unique_id(scraper):
    """Test that each job gets a unique ID"""
    scraper = JobScraper()

    job1 = scraper.add_manual_job("Title1", "Co1", "http://example.com/1")
    job2 = scraper.add_manual_job("Title2", "Co2", "http://example.com/2")

    assert job1["id"] != job2["id"]
    assert job1["id"].startswith("manual_")


def test_add_manual_job_rejects_empty_title():
    """Test validation of empty job title"""
    scraper = JobScraper()

    with pytest.raises(ValueError, match="Job title and url cannot be empty"):
        scraper.add_manual_job("", "Co", "http://example.com", "")


def test_guess_experience_level():
    """Test experience level detection"""
    scraper = JobScraper()

    assert scraper._guess_experience_level("Senior Developer", "") == "Senior"
    assert scraper._guess_experience_level("Junior Developer", "") == "Junior"
    assert scraper._guess_experience_level("Developer", "") == "Mid"


def test_add_from_url(scraper):
    """Test the quick add from URL functionality."""
    job = scraper.add_from_url("http://example.com/3", "Quick Job", "Quick Co")
    assert job["title"] == "Quick Job"
    assert job["source"] == "url_import"

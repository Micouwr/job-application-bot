import pytest
import sys
import os

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import JobApplicationBot

@pytest.fixture
def bot():
    """Pytest fixture to provide a JobApplicationBot instance."""
    return JobApplicationBot()

def test_add_manual_job_creates_valid_job_dict(bot: JobApplicationBot):
    """
    Tests that the add_manual_job method returns a well-structured job dictionary.
    """
    # 1. Define job details
    title = "Software Engineer"
    company = "TestCo"
    description = "A test job."

    # 2. Call the method
    job_dict = bot.add_manual_job(title=title, company=company, description=description)

    # 3. Assert the dictionary is created and has the expected structure
    assert isinstance(job_dict, dict)
    assert "id" in job_dict
    assert "title" in job_dict
    assert "company" in job_dict
    assert "description" in job_dict
    assert "source" in job_dict

    # 4. Assert the values are correctly assigned
    assert job_dict["title"] == title
    assert job_dict["company"] == company
    assert job_dict["description"] == description
    assert job_dict["source"] == "manual"

def test_add_manual_job_requires_title(bot: JobApplicationBot):
    """
    Tests that add_manual_job raises a ValueError if the title is empty.
    """
    with pytest.raises(ValueError, match="Job title cannot be empty"):
        bot.add_manual_job(title="  ", company="TestCo")

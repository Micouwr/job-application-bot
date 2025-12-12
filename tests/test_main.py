import pytest
import os
import sys
from unittest.mock import MagicMock

# Adjust path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import JobApplicationBot

# Mock resume data for initializing the bot
MOCK_RESUME_DATA = {
    "full_text": "Experienced software engineer.",
    "name": "Test Candidate"
}

@pytest.fixture
def bot_instance():
    """Provides an instance of JobApplicationBot with mocked dependencies."""
    # We can mock the database and other components if needed in the future
    bot = JobApplicationBot(resume_data=MOCK_RESUME_DATA)
    bot.db = MagicMock()
    bot.matcher = MagicMock()
    bot.tailor = MagicMock()
    return bot

def test_add_manual_job(bot_instance):
    """
    Tests the core logic of creating a manual job entry.
    This replaces the previous, invalid CLI tests.
    """
    # Arrange
    title = "Software Engineer"
    company = "TestCo"
    description = "A job requiring Python."
    
    # Act
    job = bot_instance.add_manual_job(title, company, description)
    
    # Assert
    assert isinstance(job, dict)
    assert job["title"] == title
    assert job["company"] == company
    assert job["description"] == description
    assert job["id"].startswith("manual_")

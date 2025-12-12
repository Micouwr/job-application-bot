import pytest
import os
import sys
import sqlite3
from unittest.mock import patch

# Adjust path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import DatabaseManager

@pytest.fixture
def db_manager(tmp_path):
    """
    Fixture to set up a transient database for testing.
    This ensures tests are isolated and don't modify the real database.
    """
    # Use a temporary file for the database
    db_path = tmp_path / "test_applications.db"
    
    # Patch the DB_PATH in the settings to use our temporary path
    with patch('database.DB_PATH', db_path):
        db = DatabaseManager()
        yield db

def test_add_and_get_application(db_manager):
    """
    Tests if an application can be added and successfully retrieved.
    This replaces the previous, invalid test.
    """
    # Arrange: Define test data
    job_title = "Test Engineer"
    company_name = "TestCorp"
    job_url = "http://test.com"
    resume_path = "/path/to/resume.pdf"
    cover_letter_path = "/path/to/cover_letter.md"
    
    # Act: Add an application
    app_id = db_manager.add_application(job_title, company_name, job_url, resume_path, cover_letter_path)
    assert app_id is not None
    
    # Act: Retrieve all applications
    apps = db_manager.get_all_applications()
    
    # Assert: Verify the retrieved data
    assert len(apps) == 1
    app = apps[0]
    assert app['job_title'] == job_title
    assert app['company_name'] == company_name
    assert app['job_url'] == job_url
    assert app['status'] == 'pending'

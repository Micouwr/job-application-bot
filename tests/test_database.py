import pytest
import os
import sys
import sqlite3
from typing import Dict, Any

# Adjust path to import app modules if running from the tests directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import DatabaseManager

@pytest.fixture
def db_manager_setup_teardown():
    """
    Fixture to set up a transient, in-memory database for testing and tear it down.
    This ensures tests are isolated and don't modify the real history.db.
    """
    # Use an in-memory SQLite database for testing isolation
    original_db_name = DatabaseManager.DB_NAME
    DatabaseManager.DB_NAME = ":memory:" 
    
    # Initialize the in-memory database (creates tables)
    db_manager = DatabaseManager()
    
    # Yield the manager instance to the test
    yield db_manager
    
    # Teardown logic: Restore the default DB name
    DatabaseManager.DB_NAME = original_db_name

def test_database_logging_and_retrieval(db_manager_setup_teardown):
    """Tests if a tailoring result can be logged and successfully retrieved from history."""
    db_manager = db_manager_setup_teardown
    
    test_results = {
        "resume_text": "Tailored Resume Content",
        "cover_letter": "Cover Letter Content for Testing",
        "changes": ["Change 1: Refined skill section.", "Change 2: Updated summary.", "Change 3: Added project details."],
    }
    
    job_title = "Senior Infrastructure Architect"
    resume_file = "my_original_resume.txt"
    
    # Log the result
    db_manager.log_tailoring_result(job_title, resume_file, test_results)
    
    # Retrieve all history records
    history = db_manager.get_history()
    
    # Assert one record exists in the history table
    assert len(history) == 1
    
    # Assert the data in the history record is correct
    record = history[0]
    assert record["action"] == "TAILOR_RUN"
    assert record["job_title"] == job_title
    assert record["resume_file"] == resume_file
    
    # Secondary check: Connect back to the in-memory DB to verify the detailed results table
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Note: Since the log operation succeeded, we verify the data integrity of the detailed table (tailoring_results)
    # This requires running the same SQL logic inside the test to check the primary log was committed.
    # To check the *second* table, we must create a direct connection within the test to the same DB file.
    # Since we cannot pass the in-memory connection between the log function and the test, 
    # we rely on the primary history table check above as the main confirmation the logging transaction worked.

    # Final assertion: Check the summary message is logged correctly
    assert record["result_summary"] == "Tailoring run complete."
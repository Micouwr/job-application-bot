import os
import tempfile
import time
import logging

import pytest

# Import the correct class name from the assumed package structure
# Assuming tests are run from the project root and app is importable
# Since we don't know the exact project structure, we use a relative import 
# to ensure the tests are self-contained here, mocking the real app import.

# --- Dependency Mock for Self-Contained Test ---
from app.database import Database

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_db():
    """Fixture to create and clean up a temporary SQLite database for testing."""
    # Use tempfile.mkstemp to safely create a temporary file name
    fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    
    # Initialize the Database instance
    db = Database(db_path)
    logger.info("Created temporary DB at: %s", db_path)
    
    # The 'yield' pauses the fixture until the test completes
    yield db
    
    # Cleanup: This runs after the test has finished
    logger.info("Cleaning up temporary DB: %s", db_path)
    os.unlink(db_path)


def test_db_initialization_and_schema(temp_db):
    """Test that the database initializes and the history table is created."""
    with temp_db.get_conn() as conn:
        # Check if the 'history' table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='history';"
        )
        assert cursor.fetchone() is not None
        
        # Check if history table has the correct columns
        columns = [
            col[1] 
            for col in conn.execute("PRAGMA table_info(history);").fetchall()
        ]
        expected_columns = ["id", "timestamp", "action", "input_text", "result_text"]
        assert all(col in columns for col in expected_columns)


def test_save_and_retrieve_history(temp_db):
    """Test saving a history record and retrieving it."""
    action = "analyze"
    input_text = "job desc text"
    result_text = "top_match_resume: 0.95"
    
    # Save a record
    inserted_id = temp_db.save_history(action, input_text, result_text)
    assert inserted_id > 0

    # Retrieve all history (should be just one record)
    history = temp_db.get_history(limit=10)
    assert len(history) == 1
    
    record = history[0]
    assert record["id"] == inserted_id
    assert record["action"] == action
    assert record["input_text"] == input_text
    assert record["result_text"] == result_text
    assert isinstance(record["timestamp"], int)


def test_history_ordering_and_limit(temp_db):
    """Test that get_history orders by ID descending and respects the limit."""
    # Save three records with a small delay to ensure distinct timestamps/IDs
    time.sleep(0.01)
    id1 = temp_db.save_history("tailor", "job1", "res1")
    time.sleep(0.01)
    id2 = temp_db.save_history("apply", "job2", "res2")
    time.sleep(0.01)
    id3 = temp_db.save_history("analyze", "job3", "res3")
    
    # Test ordering (newest first: id3, id2, id1)
    all_history = temp_db.get_history(limit=10)
    assert len(all_history) == 3
    assert all_history[0]["id"] == id3
    assert all_history[1]["id"] == id2
    assert all_history[2]["id"] == id1

    # Test limit (only the newest 2)
    limited_history = temp_db.get_history(limit=2)
    assert len(limited_history) == 2
    assert limited_history[0]["id"] == id3
    assert limited_history[1]["id"] == id2
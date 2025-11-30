import pytest
from pathlib import Path
import sys
import os

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import JobDatabase, Job


# Use a temporary database file for testing
TEST_DB_PATH = Path("test_job_app.db")

@pytest.fixture
def db():
    """Pytest fixture to set up and tear down a test database."""
    # Setup: create a new database
    database = JobDatabase(db_path=TEST_DB_PATH)
    yield database
    # Teardown: remove the database file
    os.remove(TEST_DB_PATH)

def test_insert_and_get_job(db: JobDatabase):
    """
    Tests the core functionality of inserting a job and retrieving it.
    """
    # 1. Define a sample job
    job_data = {
        "id": "test_job_123",
        "title": "Senior Python Developer",
        "company": "Test Corp",
        "description": "A job for testing purposes.",
        "url": "https://example.com/job/123",
        "status": "new"
    }

    # 2. Insert the job
    db.insert_job(job_data)

    # 3. Retrieve the job from the database
    with db.get_session() as session:
        retrieved_job = session.query(Job).filter_by(id="test_job_123").first()

    # 4. Assert that the retrieved job is not None and its data is correct
    assert retrieved_job is not None
    assert retrieved_job.title == "Senior Python Developer"
    assert retrieved_job.company == "Test Corp"
    assert retrieved_job.status == "new"

def test_get_all_jobs_empty(db: JobDatabase):
    """
    Tests that getting all jobs from an empty database returns an empty list.
    """
    all_jobs = db.get_all_jobs()
    assert isinstance(all_jobs, list)
    assert len(all_jobs) == 0

import os
import tempfile

import pytest

from database import JobDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = JobDatabase(db_path)
    yield db
    db.close()
    os.unlink(db_path)


def test_insert_job_duplicate_url(temp_db):
    """Test that duplicate URLs are rejected"""
    job = {
        "id": "test_1",
        "title": "Test Job",
        "company": "Test Co",
        "url": "https://example.com/job1",
        "source": "manual",
        "scraped_at": "2024-01-01T00:00:00",
    }

    assert temp_db.insert_job(job) is True
    assert temp_db.insert_job(job) is False  # Should reject duplicate


def test_update_status_safe(temp_db):
    """Test that status updates don't corrupt other jobs"""
    # Insert two jobs
    job1 = {
        "id": "job1",
        "title": "Job 1",
        "company": "Co",
        "url": "http://1",
        "source": "manual",
    }
    job2 = {
        "id": "job2",
        "title": "Job 2",
        "company": "Co",
        "url": "http://2",
        "source": "manual",
    }

    temp_db.insert_job(job1)
    temp_db.insert_job(job2)

    # Update status of job1
    temp_db.update_status("job1", "applied")

    # Verify job2 status is unchanged
    job2_data = temp_db.conn.execute(
        "SELECT status FROM jobs WHERE id = ?", ("job2",)
    ).fetchone()
    assert job2_data["status"] != "applied"


def test_get_pending_reviews(temp_db):
    """Test retrieving jobs that are pending review."""
    job1 = {
        "id": "job1",
        "title": "Job 1",
        "company": "Co",
        "url": "http://1",
        "source": "manual",
    }
    job2 = {
        "id": "job2",
        "title": "Job 2",
        "company": "Co",
        "url": "http://2",
        "source": "manual",
    }
    temp_db.insert_job(job1)
    temp_db.insert_job(job2)

    # Create a pending application for job1
    temp_db.save_application("job1", "resume", "cover letter", ["changes"])

    pending = temp_db.get_pending_reviews()
    assert len(pending) == 1
    assert pending[0]["id"] == "job1"


def test_get_statistics(temp_db):
    """Test calculation of database statistics."""
    job1 = {
        "id": "job1",
        "title": "Job 1",
        "company": "Co",
        "url": "http://1",
        "source": "manual",
    }
    temp_db.insert_job(job1)
    temp_db.update_match_score("job1", {"match_score": 0.9})
    temp_db.save_application("job1", "resume", "cover letter", ["changes"])
    temp_db.update_status("job1", "applied")

    stats = temp_db.get_statistics()
    assert stats["total_jobs"] == 1
    assert stats["high_matches"] == 1
    assert stats["by_status"]["applied"] == 1

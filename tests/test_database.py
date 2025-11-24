"""
Tests for the JobDatabase class.
"""

import pytest

from database import JobDatabase


@pytest.fixture
def db():
    """Returns a JobDatabase instance with an in-memory database."""
    db = JobDatabase(db_path=":memory:")
    yield db
    db.close()


def test_insert_job(db):
    """Tests that a job can be inserted into the database."""
    job = {
        "id": "123",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "source": "linkedin",
        "url": "https://example.com",
    }
    assert db.insert_job(job)
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", ("123",))
    assert cursor.fetchone() is not None


def test_update_match_score(db):
    """Tests that a job's match score can be updated."""
    job = {
        "id": "123",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "source": "linkedin",
        "url": "https://example.com",
    }
    db.insert_job(job)
    match_result = {"match_score": 0.9}
    assert db.update_match_score("123", match_result)
    cursor = db.conn.cursor()
    cursor.execute("SELECT match_score FROM jobs WHERE id = ?", ("123",))
    assert cursor.fetchone()["match_score"] == 0.9


def test_save_application(db):
    """Tests that an application can be saved to the database."""
    job = {
        "id": "123",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "source": "linkedin",
        "url": "https://example.com",
    }
    db.insert_job(job)
    assert db.save_application("123", "resume", "cover_letter", ["changes"])
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE job_id = ?", ("123",))
    assert cursor.fetchone() is not None


def test_get_pending_reviews(db):
    """Tests that pending reviews can be retrieved from the database."""
    job = {
        "id": "123",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "source": "linkedin",
        "url": "https://example.com",
    }
    db.insert_job(job)
    db.save_application("123", "resume", "cover_letter", ["changes"])
    reviews = db.get_pending_reviews()
    assert len(reviews) == 1
    assert reviews[0]["id"] == "123"


def test_get_all_jobs(db):
    """Tests that all jobs can be retrieved from the database."""
    job1 = {
        "id": "123",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "source": "linkedin",
        "url": "https://example.com",
    }
    job2 = {
        "id": "456",
        "title": "Data Scientist",
        "company": "Data Corp",
        "source": "indeed",
        "url": "https://example2.com",
    }
    db.insert_job(job1)
    db.insert_job(job2)
    jobs = db.get_all_jobs()
    assert len(jobs) == 2


def test_get_application_details(db):
    """Tests that application details can be retrieved from the database."""
    job = {
        "id": "123",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "description": "Test description",
        "source": "linkedin",
        "url": "https://example.com",
    }
    db.insert_job(job)
    db.save_application("123", "resume", "cover_letter", ["changes"])
    details = db.get_application_details("123")
    assert details["description"] == "Test description"
    assert details["tailored_resume"] == "resume"


def test_update_status(db):
    """Tests that the status of an application can be updated."""
    job = {
        "id": "123",
        "title": "Software Engineer",
        "company": "Tech Corp",
        "source": "linkedin",
        "url": "https://example.com",
    }
    db.insert_job(job)
    db.save_application("123", "resume", "cover_letter", ["changes"])
    assert db.update_status("123", "applied")
    cursor = db.conn.cursor()
    cursor.execute("SELECT status FROM applications WHERE job_id = ?", ("123",))
    assert cursor.fetchone()["status"] == "applied"

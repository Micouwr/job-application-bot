import pytest
import sys
import os

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from matcher import JobMatcher

# A sample job description for testing
SAMPLE_JOB_DESC = {
    "id": "sample1",
    "title": "Senior AI Governance Strategy Lead",
    "company": "Global Systems",
    "description": "Seeking a leader to establish ISO/IEC 42001 compliant AI Governance frameworks. Must have deep experience in Python automation for Service Desk Triage and risk management.",
    "requirements": "10+ years experience, expert in Network Security and KPI reporting. Senior level role.",
}

@pytest.fixture
def matcher():
    """Pytest fixture to provide a JobMatcher instance."""
    # The matcher will be initialized with the default RESUME_DATA from config
    return JobMatcher()

def test_match_job_returns_score(matcher: JobMatcher):
    """
    Tests that the match_job method returns a dictionary with a valid match_score.
    """
    # 1. Run the matcher
    result = matcher.match_job(SAMPLE_JOB_DESC)

    # 2. Assert that the result is a dictionary and contains the 'match_score' key
    assert isinstance(result, dict)
    assert "match_score" in result

    # 3. Assert that the match score is a float between 0 and 1
    score = result["match_score"]
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0

def test_high_relevance_job_gets_high_score(matcher: JobMatcher):
    """
    Tests that a highly relevant job description receives a high match score.
    """
    # 1. Run the matcher on the sample job, which is highly relevant to the resume
    result = matcher.match_job(SAMPLE_JOB_DESC)

    # 2. Assert that the score is above a reasonable threshold for a good match
    # This confirms the weighted skills and experience matching is working.
    # NOTE: The threshold is set to a realistic baseline, not an ideal score.
    score = result["match_score"]
    assert score > 0.3, "A highly relevant job should score higher than 30%"

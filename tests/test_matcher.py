"""
Tests for the JobMatcher class.
"""

import pytest

from matcher import JobMatcher


@pytest.fixture
def job_matcher():
    """Returns a JobMatcher instance with sample resume data."""
    resume_data = {
        "skills": {
            "technical": ["Python", "AWS"],
        },
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "dates": "2020-2023",
                "skills_used": ["Python", "AWS"],
                "achievements": ["Developed a new feature."],
            }
        ],
    }
    return JobMatcher(resume_data)


def test_skills_match_exact(job_matcher):
    """Tests a perfect skill match."""
    job_text = "python aws"
    score, matched, missing = job_matcher._calculate_skills_match(job_text)
    assert score == 1.0
    assert "Python" in matched
    assert "Aws" in matched
    assert not missing


def test_experience_match(job_matcher):
    """Tests that experience is correctly matched."""
    job_text = "software engineer"
    score, relevant_exp = job_matcher._calculate_experience_match(job_text)
    assert score > 0
    assert "Software Engineer at Tech Corp" in relevant_exp[0]


def test_keyword_match(job_matcher):
    """Tests that keywords are correctly matched."""
    job_text = "help desk leadership"
    score, keyword_matches = job_matcher._calculate_keyword_match(job_text)
    assert score > 0
    assert "help desk" in keyword_matches
    assert "leadership" in keyword_matches

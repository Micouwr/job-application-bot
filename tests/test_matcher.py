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

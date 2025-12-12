import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Adjust path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from matcher import JobMatcher

# Mock data for Matcher test
MOCK_JOB = {
    "title": "Software Engineer",
    "company": "TestCo",
    "description": "We need a Python expert.",
}

# Mock resume data to avoid dependency on real files
MOCK_RESUME_DATA = {
    "full_text": "I am a Python expert with 5 years of experience.",
    "name": "Test Candidate"
}

@patch('matcher.prompts')
def test_job_matcher_initialization_and_run(mock_prompts):
    """
    Tests if the JobMatcher class initializes and the match_job method runs.
    This replaces the previous, invalid test for the obsolete Matcher class.
    """
    # Arrange: Mock the prompt generation to isolate the test
    mock_prompts.generate.return_value = '''
    {
        "match_score": 0.9,
        "recommendation": "STRONG_MATCH",
        "strengths": ["Python expert"],
        "gaps": [],
        "reasoning": "Candidate is a Python expert."
    }
    '''
    
    # Act & Assert: The matcher should initialize without errors
    # We pass in mock resume data to make the test self-contained
    matcher = JobMatcher(resume_data=MOCK_RESUME_DATA)
    
    # Act: Run the matching logic
    result = matcher.match_job(MOCK_JOB)
    
    # Assert: The result should be a dictionary with the expected score
    assert isinstance(result, dict)
    assert result['match_score'] == 0.9
    assert result['recommendation'] == "STRONG_MATCH"

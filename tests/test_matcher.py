import pytest
import os
import sys
from typing import Dict, Any

# Adjust path to import app modules if running from the tests directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.matcher import Matcher

# Mock data for Matcher test
MOCK_JOB_DESC = "We require an expert in Python, AWS Cloud, and Linux systems administration."
MOCK_RESUME_1 = "My background includes extensive use of Python scripting for automation on Linux servers. I have AWS certifications."
MOCK_RESUME_2 = "I am a fantastic graphic designer specializing in Photoshop and illustration."


def test_matcher_scoring_accuracy():
    """Tests if the matcher correctly identifies keyword overlap and assigns a higher score."""
    matcher = Matcher(match_threshold=0.5)
    resumes = {
        "good_match.txt": MOCK_RESUME_1,
        "bad_match.txt": MOCK_RESUME_2,
    }
    
    # Run the matching algorithm
    results = matcher.top_matches(resumes, MOCK_JOB_DESC, top_n=2)
    
    assert len(results) == 2
    
    # Extract the scores for verification
    score_1 = next(score for name, score in results if name == "good_match.txt")
    score_2 = next(score for name, score in results if name == "bad_match.txt")
    
    # Assertions based on expected keyword overlap
    assert score_1 > 0.5  # Good match should pass the threshold
    assert score_2 < 0.2  # Bad match should have a very low score
    assert score_1 > score_2 # The good match must score higher
import pytest
import os
import sys
from unittest.mock import MagicMock
from typing import List

# Adjust path to import app modules if running from the tests directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tailor import ResumeTailor, APIClient # APIClient included for mocking

# Mock response structure for ResumeTailor._parse_response test
MOCK_AI_RESPONSE = """
[START_RESUME]
# Tailored Resume
- Experience 1: Focused on cloud architecture.
- Experience 2: Highlighted Python scripting.
[END_RESUME]

[START_COVER_LETTER]
Dear Hiring Manager,

I am writing to express my interest in the Infrastructure Role. 
I noticed your recent acquisition of 'TechFirm ABC' via a Google search, which perfectly aligns with my cloud migration skills.

Sincerely,
Candidate Name
[END_COVER_LETTER]

[START_CHANGES]
Reordered sections for relevance.
Emphasized cloud certifications.
Removed irrelevant volunteer work.
[END_CHANGES]
"""

def test_tailor_parsing_success():
    """Tests if the _parse_response method correctly extracts content from the structured tags."""
    # Mock the client to prevent actual API calls and configuration errors
    tailor = ResumeTailor(api_client=MagicMock(spec=APIClient)) 
    
    parsed_results = tailor._parse_response(MOCK_AI_RESPONSE)
    
    assert "resume_text" in parsed_results
    assert "cover_letter" in parsed_results
    assert "changes" in parsed_results
    
    # Check resume text content
    assert "cloud architecture" in parsed_results["resume_text"]
    
    # Check cover letter content (specifically the part referencing search grounding)
    assert "acquisition of 'TechFirm ABC'" in parsed_results["cover_letter"]
    
    # Check changes list format
    assert isinstance(parsed_results["changes"], List)
    assert len(parsed_results["changes"]) == 3
    assert parsed_results["changes"][1] == "Emphasized cloud certifications."


def test_tailor_parsing_missing_tag_raises_error():
    """Tests if parsing fails gracefully when a mandatory tag is missing."""
    tailor = ResumeTailor(api_client=MagicMock(spec=APIClient))
    
    # Remove the mandatory [END_RESUME] tag to force a failure
    invalid_response = MOCK_AI_RESPONSE.replace("[END_RESUME]", "MISSING TAG")
    
    with pytest.raises(ValueError, match="Malformed AI response"):
        tailor._parse_response(invalid_response)
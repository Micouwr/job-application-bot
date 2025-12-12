import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Adjust path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tailor import ResumeTailor

# Mock resume data for initializing the tailor
MOCK_RESUME_DATA = {
    "full_text": "Experienced software engineer.",
    "name": "Test Candidate"
}

# This is the mock response we will tell the Gemini API to return
MOCK_API_RESPONSE_TEXT = """
```json
{
    "resume_text": "This is the tailored resume.",
    "cover_letter": "This is the tailored cover letter."
}
```
"""

@patch('tailor.genai.GenerativeModel')
def test_generate_tailored_resume_success(MockGenerativeModel):
    """
    Tests that the tailor correctly calls the API and parses the JSON response.
    This replaces the previous, invalid parsing tests.
    """
    # Arrange: Configure the mock model and its response
    mock_model_instance = MockGenerativeModel.return_value
    mock_response = MagicMock()
    mock_response.text = MOCK_API_RESPONSE_TEXT
    mock_model_instance.generate_content.return_value = mock_response
    
    # Act: Initialize the tailor and call the method
    tailor = ResumeTailor(resume_data=MOCK_RESUME_DATA)
    result = tailor.generate_tailored_resume(
        job_description="A job for a Python dev.",
        job_title="Python Developer",
        company="TestCo"
    )
    
    # Assert: Verify the results
    assert result["success"] is True
    assert "This is the tailored resume." in result["resume_text"]
    assert "This is the tailored cover letter." in result["cover_letter"]
    
    # Assert that the API was called
    mock_model_instance.generate_content.assert_called_once()

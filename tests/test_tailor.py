"""
Tests for the ResumeTailor class.
"""

from unittest.mock import MagicMock, patch

import pytest

from tailor import ResumeTailor


@pytest.fixture
def resume_data():
    """Provides sample resume data for tests."""
    return {
        "summary": "A software engineer with 5 years of experience.",
        "experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "achievements": ["Developed a new feature."],
            }
        ],
    }


@patch("tailor.genai.GenerativeModel")
def test_tailor_application(mock_generative_model, resume_data):
    """
    Tests that the application tailoring is working correctly, using a mock for the Gemini API.
    """
    # Create a mock for the model's response
    mock_response = MagicMock()
    mock_response.text = """
[START_RESUME]
This is the tailored resume.
[END_RESUME]
[START_COVER_LETTER]
This is the tailored cover letter.
[END_COVER_LETTER]
[START_CHANGES]
- Rewrote the summary.
[END_CHANGES]
    """
    # Configure the mock model instance to return the mock response
    mock_model_instance = mock_generative_model.return_value
    mock_model_instance.generate_content.return_value = mock_response

    # Instantiate ResumeTailor - the mocks are active here
    resume_tailor = ResumeTailor(resume_data)

    job = {
        "title": "Software Engineer",
        "company": "Test Co",
        "description": "A job description.",
    }
    match = {
        "match_score": 0.9,
        "matched_skills": ["Python"],
        "relevant_experience": ["Software Engineer at Tech Corp"],
    }

    result = resume_tailor.tailor_application(job, match)

    # Assertions
    assert result["resume_text"] == "This is the tailored resume."
    assert result["cover_letter"] == "This is the tailored cover letter."
    assert "- Rewrote the summary." in result["changes"]

    # Check that the mock was called
    mock_model_instance.generate_content.assert_called_once()

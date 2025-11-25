from unittest.mock import MagicMock, patch

import pytest

from config.settings import RESUME_DATA
from tailor import ResumeTailor


@pytest.fixture
def tailor():
    return ResumeTailor(RESUME_DATA)


def test_parse_response_valid_format(tailor):
    """Test parsing valid Gemini API response"""
    response = """
[START_RESUME]Tailored resume here[END_RESUME]
[START_COVER_LETTER]Cover letter here[END_COVER_LETTER]
[START_CHANGES]Added AWS cert, emphasized leadership[END_CHANGES]
    """

    result = tailor._parse_response(response)

    assert "Tailored resume here" in result["resume_text"]
    assert "Cover letter here" in result["cover_letter"]
    assert "Added AWS cert" in result["changes"][0]


def test_parse_response_empty_changes(tailor):
    """Test parsing response with no changes"""
    response = """
[START_RESUME]Resume[END_RESUME]
[START_COVER_LETTER]Cover[END_COVER_LETTER]
[START_CHANGES][END_CHANGES]
    """

    result = tailor._parse_response(response)

    assert result["changes"] == []  # Should be empty list, not ['']


def test_parse_response_malformed(tailor):
    """Test handling of malformed AI response"""
    response = "Invalid response without tags"

    with pytest.raises(ValueError):
        tailor._parse_response(response)


@patch("tailor.genai.GenerativeModel")
def test_tailor_application_api_call(mock_model_class):
    """Test that the tailor_application method calls the Gemini API correctly."""
    # Setup mock
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value.text = """
[START_RESUME]resume[END_RESUME]
[START_COVER_LETTER]cover[END_COVER_LETTER]
[START_CHANGES]changes[END_CHANGES]
    """
    mock_model_class.return_value = mock_model_instance

    tailor = ResumeTailor(RESUME_DATA)
    job = {"title": "Test Job", "description": "..."}
    match = {"match_score": 0.8}

    tailor.tailor_application(job, match)

    # Assert that the API was called
    mock_model_instance.generate_content.assert_called_once()

from unittest.mock import MagicMock, patch

import pytest

# Corrected import path and class name
from app.tailor import ResumeTailor, APIClient


@pytest.fixture
def tailor():
    """Returns a ResumeTailor instance."""
    # The tailor no longer needs RESUME_DATA for initialization
    return ResumeTailor()


def test_parse_response_valid_format(tailor):
    """Test parsing valid structured AI response"""
    response = """
[START_RESUME]Tailored resume here[END_RESUME]
[START_COVER_LETTER]Cover letter here[END_COVER_LETTER]
[START_CHANGES]Added AWS cert
Emphasized leadership[END_CHANGES]
    """

    result = tailor._parse_response(response)

    assert "Tailored resume here" in result["resume_text"]
    assert "Cover letter here" in result["cover_letter"]
    assert "Added AWS cert" in result["changes"][0]
    assert "Emphasized leadership" in result["changes"][1]


def test_parse_response_empty_changes(tailor):
    """Test parsing response with no changes listed."""
    response = """
[START_RESUME]Resume[END_RESUME]
[START_COVER_LETTER]Cover[END_COVER_LETTER]
[START_CHANGES]
[END_CHANGES]
    """

    result = tailor._parse_response(response)

    assert result["changes"] == []  # Should be empty list


def test_parse_response_malformed_resume_tags(tailor):
    """Test handling of malformed AI response (missing mandatory resume tags)."""
    response = "Invalid response without tags, just text."

    with pytest.raises(ValueError, match="Missing mandatory \[RESUME\] tags"):
        tailor._parse_response(response)


# We need to mock the underlying APIClient call, not a specific LLM SDK
@patch.object(APIClient, 'call_model')
def test_tailor_application_api_call(mock_call_model):
    """Test that the tailor_application method calls the underlying APIClient correctly."""
    
    # Setup mock to return a valid structured response
    mock_call_model.return_value = """
[START_RESUME]resume[END_RESUME]
[START_COVER_LETTER]cover[END_COVER_LETTER]
[START_CHANGES]changes[END_CHANGES]
    """

    tailor = ResumeTailor()
    
    # Mock input data (we don't need the full job/match dicts for this test, just strings)
    mock_resume_text = "Original resume content"
    mock_job_text = "Job description content"

    result = tailor.tailor_application(mock_resume_text, mock_job_text)

    # Assert that the APIClient was called once
    mock_call_model.assert_called_once()
    
    # Assert the final prompt contains both pieces of input text
    prompt = mock_call_model.call_args[0][0]
    assert "Original resume content" in prompt
    assert "Job description content" in prompt
    
    # Assert the function returns the parsed dictionary
    assert isinstance(result, dict)
    assert result["resume_text"] == "resume"
#!/usr/bin/env python3
"""
Integration test: Verify the core AI tailoring pipeline.
"""
import unittest.mock
import sys
import json
from pathlib import Path

# CRITICAL FIX: Point to project root (parent of tests/)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the function that was actually changed
from tailor import process_and_tailor_from_gui

def test_tailoring_pipeline():
    """
    Test that process_and_tailor_from_gui correctly calls the AI,
    parses the JSON response, and returns the expected content.
    """
    print("=== Testing Core Tailoring Pipeline ===")
    
    # Test data
    resume = "This is a resume."
    job_description = "This is a job description."
    output_path = "/tmp"
    role_level = "Senior"

    # Mock responses
    mock_api_response = {
        "tailored_resume": "This is the tailored resume content.",
        "cover_letter": "This is the generated cover letter content."
    }
    
    # The AI model returns an object with a 'text' attribute containing a JSON string.
    mock_response_object = unittest.mock.Mock()
    mock_response_object.text = json.dumps(mock_api_response)

    # We need to mock two API calls: one for extract_job_details and one for generate_content
    with unittest.mock.patch('tailor.extract_job_details') as mock_extract, \
         unittest.mock.patch('tailor.genai.GenerativeModel.generate_content') as mock_generate:

        # Configure the mocks to return our fake data
        mock_extract.return_value = {"company_name": "Mock Company", "job_title": "Mock Job"}
        mock_generate.return_value = mock_response_object

        # Call the function we want to test
        result = process_and_tailor_from_gui(resume, job_description, output_path, role_level)

        # Assertions
        assert mock_extract.called, "extract_job_details was not called."
        assert mock_generate.called, "generate_content was not called."

        assert result is not None, "Function returned None."
        assert "resume_text" in result, "Result dictionary is missing 'resume_text' key."
        assert "cover_letter" in result, "Result dictionary is missing 'cover_letter' key."

        assert result["resume_text"] == mock_api_response["tailored_resume"], "Resume text does not match mock."
        assert result["cover_letter"] == mock_api_response["cover_letter"], "Cover letter does not match mock."

    print("\n=== TEST PASSED ===")
    return True

if __name__ == "__main__":
    try:
        test_tailoring_pipeline()
        sys.exit(0)
    except Exception as e:
        print(f"\n=== TEST FAILED ===")
        print(f"Error: {e}")
        sys.exit(1)

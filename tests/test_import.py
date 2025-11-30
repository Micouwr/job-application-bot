import pytest
from unittest.mock import patch, MagicMock
from main import JobApplicationBot
import os
import sys

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def bot():
    """Pytest fixture to provide a JobApplicationBot instance."""
    return JobApplicationBot()

@patch('main.JobApplicationBot.run_pipeline_async')
def test_import_jobs_json_calls_pipeline(mock_run_pipeline_async, bot: JobApplicationBot):
    """
    Tests that import_jobs correctly parses a JSON file and calls the pipeline.
    """
    # 1. Get the path to the sample jobs file
    file_path = "tests/sample_jobs.json"

    # Create a mock future object that the pipeline returns
    mock_future = MagicMock()
    mock_run_pipeline_async.return_value = mock_future

    # 2. Call the import_jobs method
    bot.import_jobs(file_path)

    # 3. Assert that run_pipeline_async was called once
    mock_run_pipeline_async.assert_called_once()

    # 4. Assert that the future's result() method was called (to ensure it blocks)
    mock_future.result.assert_called_once()

    # 5. Inspect the arguments passed to the pipeline
    args, kwargs = mock_run_pipeline_async.call_args
    assert "manual_jobs" in kwargs
    manual_jobs = kwargs["manual_jobs"]
    assert isinstance(manual_jobs, list)
    assert len(manual_jobs) == 2
    assert manual_jobs[0]["title"] == "Test Job 1"
    assert manual_jobs[1]["company"] == "Test Co 2"

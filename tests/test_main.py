from unittest.mock import patch

import pytest

from main import JobApplicationBot


@patch(
    "builtins.input",
    side_effect=[
        "Test Job",
        "Test Company",
        "http://test.com",
        "Test Location",
        "Test description",
        "",
        "done",
    ],
)
@patch("main.JobApplicationBot.run_pipeline")
def test_run_interactive_loop(mock_run_pipeline, mock_input):
    """
    Tests that the interactive loop collects job details and calls the pipeline.
    """
    bot = JobApplicationBot()
    bot.run_interactive()

    # Asserts that the pipeline was called, which means the loop was entered and exited correctly
    mock_run_pipeline.assert_called_once()

    # Check that the pipeline was called with the job we "entered"
    _, call_kwargs = mock_run_pipeline.call_args
    assert "manual_jobs" in call_kwargs
    assert len(call_kwargs["manual_jobs"]) == 1
    assert call_kwargs["manual_jobs"][0]["title"] == "Test Job"


@patch("builtins.input", side_effect=["1", "quit"])
def test_approve_interactive_loop(mock_input):
    """
    Tests the interactive approval loop.
    """
    bot = JobApplicationBot()

    # Manually add a job and a pending application to the database
    job = bot.add_manual_job("Test Job", "Test Co", "http://test.com")
    bot.db.insert_job(job)
    bot.db.save_application(job["id"], "resume", "cover", ["changes"])

    with patch.object(bot, "approve_application") as mock_approve:
        bot.approve_interactive()
        mock_approve.assert_called_once_with(job["id"])

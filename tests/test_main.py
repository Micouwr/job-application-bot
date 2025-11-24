"""
Tests for the JobApplicationBot class.
"""

from unittest.mock import MagicMock, patch

from main import JobApplicationBot


@patch("main.validate_config")
def test_add_manual_job(mock_validate_config):
    """Tests that a job can be added manually."""
    bot = JobApplicationBot()
    bot.scraper = MagicMock()
    bot.add_manual_job(
        title="Software Engineer",
        company="Tech Corp",
        url="https://example.com",
    )
    bot.scraper.add_manual_job.assert_called_once_with(
        "Software Engineer",
        "Tech Corp",
        "https://example.com",
        "",
        "",
    )

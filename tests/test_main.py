import pytest
import sys
from unittest.mock import patch, mock_open

# Import the main function from the CLI entry point
from cli.main import main 

# Define mock content for the files
MOCK_JOB_TEXT = "The job requires Python, SQL, and AI Certification."
MOCK_RESUME_A = "I have experience with Python and SQL."
MOCK_RESUME_B = "I have an AI Certification."

# Helper function to configure the mock file reading for the job and two resumes
def configure_mock_file_reads(mock_file_open):
    """Sets up the mock_open side effects for job.txt, resume_a.txt, and resume_b.txt."""
    # We chain mock_open calls for each file read operation in cli/main.py
    mock_file_open.side_effect = [
        # 1. Read job file
        patch('builtins.open', mock_open(read_data=MOCK_JOB_TEXT)).return_value,
        # 2. Read resume_a.txt
        patch('builtins.open', mock_open(read_data=MOCK_RESUME_A)).return_value,
        # 3. Read resume_b.txt
        patch('builtins.open', mock_open(read_data=MOCK_RESUME_B)).return_value,
    ]


@patch("app.bot.JobApplicationBot")
@patch("builtins.open")
def test_cli_analyze_mode(mock_file_open, MockJobApplicationBot):
    """
    Tests that the CLI correctly reads files and delegates to bot.analyze_job,
    and prints the results.
    """
    # Configure file content
    configure_mock_file_reads(mock_file_open)
    
    # Configure the mock bot's return value
    mock_bot_instance = MockJobApplicationBot.return_value
    mock_bot_instance.analyze_job.return_value = [
        ("resume_b.txt", 0.85),
        ("resume_a.txt", 0.60)
    ]

    # Command line arguments for analysis
    args = [
        "--analyze", 
        "--job-file", "job.txt", 
        "--resume-files", "resume_a.txt", "resume_b.txt"
    ]

    # Run the main function and capture output
    with patch("sys.stdout") as mock_stdout:
        exit_code = main(args)

    assert exit_code == 0
    
    # Verify the core method was called with the right data structure
    MockJobApplicationBot.assert_called_once()
    mock_bot_instance.analyze_job.assert_called_once()
    
    # Check that the results were printed correctly
    output_lines = [call[0][0] for call in mock_stdout.write.call_args_list]
    assert "resume_b.txt: 0.850" in output_lines
    assert "resume_a.txt: 0.600" in output_lines


@patch("app.bot.JobApplicationBot")
@patch("builtins.open")
def test_cli_tailor_mode(mock_file_open, MockJobApplicationBot):
    """
    Tests that the CLI correctly reads files and delegates to bot.tailor_resume
    using the first provided resume.
    """
    # Configure file content
    configure_mock_file_reads(mock_file_open)
    
    # Configure the mock bot's return value
    mock_bot_instance = MockJobApplicationBot.return_value
    mock_tailored_text = "This is the tailored resume text from the LLM."
    mock_bot_instance.tailor_resume.return_value = mock_tailored_text

    # Command line arguments for tailoring (uses the first resume: resume_a.txt)
    args = [
        "--tailor", 
        "--job-file", "job.txt", 
        "--resume-files", "resume_a.txt", "resume_b.txt"
    ]

    # Run the main function and check for the informative logging message
    with patch("sys.stdout"), patch("logging.Logger.info") as mock_log_info:
        exit_code = main(args)

    assert exit_code == 0
    
    # Check that the bot's core method was called
    mock_bot_instance.tailor_resume.assert_called_once()
    
    # Verify the informative log about which resume was picked (based on our last refinement)
    mock_log_info.assert_any_call("Tailoring selected resume: %s", "resume_a.txt")
    
    # Verify the call was made using the first resume text (MOCK_RESUME_A)
    call_args, _ = mock_bot_instance.tailor_resume.call_args
    assert call_args[0] == MOCK_RESUME_A
    assert call_args[1] == MOCK_JOB_TEXT


@patch("app.bot.JobApplicationBot")
@patch("logging.Logger.error")
def test_cli_no_job_file_failure(mock_log_error, MockJobApplicationBot):
    """Test that the application exits gracefully with an error if --job-file is missing."""
    # Arguments list is missing --job-file
    args = ["--analyze"]
    
    # Run the main function
    exit_code = main(args)
    
    # Check for the expected exit code (2) and error logging
    assert exit_code == 2
    mock_log_error.assert_called_once_with("Please pass --job-file")
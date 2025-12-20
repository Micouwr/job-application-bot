# Contextual Recall - Job Application Bot Project

## Who I Am and My Role

I am a Gemini API Coding Expert with extremely high standards for clean, error-free code. My role is to ensure there are no errors, bugs, crashes, or any other issues in the codebase. I hold myself to the highest standards of code quality and knowledge, maintaining strict adherence to clean coding practices while working with the Job Application Bot - an AI-powered resume tailoring application that helps users optimize their resumes for specific job applications using Google's Gemini API.

My expertise encompasses:
- Implementing robust, error-free features and enhancements
- Rigorously debugging and eliminating all issues
- Enforcing strict code quality standards with zero tolerance for bugs
- Maintaining pristine architectural integrity while delivering solutions
- Ensuring all code meets the highest standards of reliability and performance

## Golden Rules - NON-NEGOTIABLE Standards

These rules are enforced with absolute strictness and must be followed without exception:

### Rule #1: NEVER ASSUME OR GUESS + DOCUMENT FACTUALLY
- Explicitly request file contents when needed
- No fixes based on "probably" - verify with diagnostics
- Check file existence with `os.path.exists()` before reading
- Confirm method signatures match before calling
- Validate user input types/range before processing
- Test API responses (e.g., `response.status_code == 200`)
- Cross-reference documentation with actual code

### Rule #2: VERIFY BEFORE AND AFTER FIXING
- Do not rebuild until imports are proven working
- Show exact findings before proposing changes
- Reproduce bugs: `print(f"Before: {variable}")`
- Check method counts: `grep -c "def " file.py`
- Validate ASCII: `python3 -c "print(max(ord(c) for c in open('file.py').read()))"`
- Import verify: `python3 -c "import module"`
- Document bug state: "Before: X, After: Y"

### Rule #3: COMPLETE FILE CONTENTS ONLY
- Provide full, unedited file contents - no summaries
- Use proper code blocks with filenames
- Atomic operations: replace entire methods or files
- No partial method replacements
- Full context: imports, classes, related functions
- No truncations that obscure architecture

### Rule #4: SAVE POINTS ARE MANDATORY
- Document every major state change with full context
- State Change Context: What & why
- Before State: "Do not proceed until..."
- User Authority: Final approval required
- Full Context: Code state, environment, decisions
- Failure Documentation: What, why, how fixed, lessons

### Rule #5: MAINTAIN ARCHITECTURAL INTEGRITY + NO BAND-AIDS
- Surgical fixes only - no breaking changes
- No temporary workarounds or patches
- Preserve all existing functionality
- Root cause fixes only
- No backup files, temporary scripts, duplicate databases
- Sanitize at source, not downstream

### Rule #6: NO UNICODE ARTIFACTS EVER
- NO em dashes (–) - use plain hyphens "-"
- NO emojis - use ASCII text only
- NO Unicode quotes - use ASCII ' and "
- Max ASCII ≤127 before every commit
- Violations cause shell/Python parsing failures

## Repository Link

GitHub Repository: https://github.com/Micouwr/job-application-bot

## What We've Done

We've successfully implemented and fixed several critical features and issues:

1. **Enhanced Role Definitions Tooltip**
   - Improved role level definitions with detailed explanations for each level
   - Fixed tooltip cutoff issue by implementing a scrollable text widget
   - Added proper positioning to ensure visibility on screen

2. **Tab Reordering**
   - Moved OUTPUT & LOGS tab to the final position as requested

3. **Date Formatting Fix**
   - Fixed date formatting issue in Tailored Documents tab
   - Increased column width to prevent header cutoff

4. **Resume Content Integrity**
   - Ensured no embellishments in tailored resumes - only factual information
   - Removed unwanted headers from resume content
   - Fixed name spacing issues

5. **Job Description Storage Feature**
   - Implemented persistent storage for job descriptions alongside tailored resumes and cover letters
   - Modified database schema to include job_description_path column
   - Updated application logic to save job descriptions to files and store paths in database
   - Enhanced UI to display job descriptions in Tailored Documents tab with three-column layout

6. **Automatic Job Detail Extraction**
   - Implemented AI-powered extraction of job title and company from job descriptions
   - Created new function in match_analyzer.py to extract these details using Gemini API
   - Modified start_tailoring method to automatically populate fields when missing

7. **PDF Export Improvements**
   - Removed unwanted header from exported PDFs
   - Fixed bullet point styling to use smaller, more professional dots

## What We Are Doing Now

Currently, we're in a waiting period due to Gemini API rate limiting:
- The API has reached its free tier limit of 20 requests per day for the `gemini-2.5-flash` model
- This prevents us from testing AI-powered features until the quota resets
- However, all UI and structural fixes have been completed and pushed to the repository

## What We Will Be Doing

After the rate limit resets, we'll focus on:

1. **Comprehensive Testing**
   - Verify all implemented features work correctly with live AI integration
   - Test automatic job title/company extraction functionality
   - Validate job description storage and retrieval workflows
   - Ensure PDF exports meet all requirements

2. **Further Enhancements**
   - Continue refining the user experience based on your feedback
   - Explore additional AI-powered features for resume optimization
   - Improve error handling and user guidance

3. **Documentation Updates**
   - Update README and user guides to reflect new features
   - Document the job description storage workflow
   - Provide clear instructions for the automatic extraction feature

4. **Performance Optimization**
   - Review and optimize AI prompt engineering
   - Improve response handling and error recovery
   - Enhance overall application stability
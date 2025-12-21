# Contextual Recall - CareerForge AI Project

## Who I Am and My Role

I am a Gemini API Coding Expert with extremely high standards for clean, error-free code. My role is to ensure there are no errors, bugs, crashes, or any other issues in the codebase. I hold myself to the highest standards of code quality and knowledge, maintaining strict adherence to clean coding practices while working with CareerForge AI - an AI-powered resume tailoring application that helps users optimize their resumes for specific job applications using Google's Gemini API.

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

GitHub Repository: https://github.com/Micouwr/careerforge-ai

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

8. **Application Renaming**
   - Changed application name from "Job Application Bot" to "CareerForge AI"
   - Updated all references in code and documentation
   - Updated window titles and internal references

9. **UI Modernization**
   - Integrated ttkthemes for modern, clean UI appearance
   - Applied the "arc" theme for contemporary look
   - Enhanced all tabs with consistent styling and better layouts
   - Improved visual hierarchy with bold titles and clear section headings

10. **Enhanced Custom Prompt Management**
    - Added variable reference section with available template variables
    - Added built-in examples section showing system prompt examples
    - Added "Load Example" button to easily load and modify built-in templates
    - Added "Preview Variables" button to visualize variable substitution
    - Added template validation to ensure proper prompt structure
    - Improved default template with proper structure and formatting

11. **GUI-Based Configuration**
    - Added Settings/Preferences tab for configuring minimum match threshold
    - Implemented slider control for adjusting threshold from 50% to 95%
    - Added manual input field for precise threshold values
    - Added real-time feedback display for current threshold value
    - Added Apply and Reset to Default buttons
    - Added guidelines for recommended threshold values

12. **Data Privacy Fixes**
    - Removed all hardcoded personal information ("Michelle Nicole") from resume templates
    - Updated default location from "San Francisco" to "Louisville, KY"
    - Updated all contact information to generic placeholders

13. **Icon System Overhaul**
    - Fixed empty computer.png file by copying valid image
    - Enhanced icon loading logic to try multiple formats (ICO, ICNS, PNG)
    - Added support for CareerForge AI branded icons in multiple formats
    - Implemented proper fallback chain for cross-platform compatibility

## What We Are Doing Now

Currently, we're focusing on comprehensive documentation updates and visual improvements:

1. **README Documentation Enhancement**
   - Updated Visual Guides section with proper CareerForge AI images
   - Replaced outdated computer.png with CareerForge_AI.png for application interface
   - Properly sized images for optimal web display (400x400 pixels)
   - Organized Application Icons section to showcase all platform-specific icons

2. **Image Asset Management**
   - Created appropriately sized versions of CareerForge AI icon for different uses
   - Ensured consistent branding across all visual elements
   - Optimized image files for web performance while maintaining quality

## What We Will Be Doing

Moving forward, we'll focus on comprehensive testing and quality assurance:

1. **Testing Phase**
   - Conduct thorough testing of all implemented features with live AI integration
   - Verify automatic job title/company extraction functionality
   - Validate job description storage and retrieval workflows
   - Test PDF export functionality across different platforms
   - Ensure all GUI elements work correctly

2. **Quality Assurance**
   - Perform cross-platform compatibility testing
   - Verify icon display works correctly on macOS and Windows
   - Test all user workflows from start to finish
   - Validate data integrity and privacy measures

3. **Performance Optimization**
   - Review and optimize AI prompt engineering
   - Improve response handling and error recovery
   - Enhance overall application stability
   - Optimize resource usage and startup times

## Current Status: TESTING PHASE

We are now entering a rigorous testing phase before implementing any further changes. A comprehensive [TESTING_PLAN.md](TESTING_PLAN.md) has been created to guide this process. All core functionality will be validated including:

- Application launch and UI rendering
- Job management and import features
- Resume tailoring with AI integration
- Document export in multiple formats
- Cross-platform compatibility
- Data privacy and security measures

No further development will proceed until all tests pass successfully.
# Job Application Bot

AI-Powered Resume Tailoring for IT/DevOps/AI Governance Roles
[Golden Rules: 6/6 Compliance] [Version: v2.1.0] [Python: 3.9+] [License: MIT]

---

## What's New in v2.1.0 (SAVE POINT #155)

AI Match Analysis Engine - Stop wasting time on poor-fit jobs!

- Smart Compatibility Scoring - AI analyzes your resume vs job description
- Detailed Match Breakdown - See strengths, gaps, and recommendations
- Threshold Enforcement - Only tailor resumes for jobs you are qualified for
- Secure Prompt Management - Curated dropdown, no filesystem browsing
- Golden Rules Compliance - 6/6 strict quality standards met

---

## Quick Start (3 Minute Setup)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure API Key
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY from https://makersuite.google.com/app/apikey
```

### Step 3: Launch Application
```bash
python gui/tkinter_app.py
```

---

## User Guide: The AI-Powered Workflow

### Step-by-Step Instructions

#### 1. Job Analysis Tab
- Paste detailed job description (minimum 100 characters)
- IMPORTANT: Job title and company are NOT required for analysis
- Click "Analyze Match" button

#### 2. Review Match Score
- Green (>=70%): Strong match! "Start Tailoring" button enabled
- Red (<70%): Poor match. Button disabled until score improves
- Score displays in real-time: "Match Score: 85%"

#### 3. Detailed Match Breakdown
Click the score to see comprehensive analysis:
- Overall Score (0-100%)
- Skills Match (% alignment)
- Experience Match (% alignment)
- Keywords Match (% alignment)
- Strengths (what you have)
- Gaps (what you're missing)
- Recommendations (improvement suggestions)

#### 4. Complete Job Details
If score is acceptable:
- Fill Job Title (for file naming)
- Fill Company (for file naming)
- Fill Job URL (optional, for tracking)

#### 5. Start AI Tailoring
- Click "Start Tailoring" (only enabled if score >= 70%)
- AI generates personalized resume and cover letter
- Files saved automatically to output/ folder
- Confirmation shows exact file paths

---

## Configuration

### MIN_MATCH_THRESHOLD
Edit config/settings.py to adjust minimum match score:
```python
MIN_MATCH_THRESHOLD = 70  # Default: 70%
```

### Custom Prompt Templates
Create tailored prompts in prompts/user/ directory:
1. Save as .txt.j2 files
2. Use variables: {role_level}, {company_name}, {job_title}, {job_description}, {resume_text}
3. Select from curated dropdown in "Custom Prompts" tab

---

## Token Management

### GitHub Authentication (Required for Git Operations)
GitHub disabled password authentication. You need a Personal Access Token (PAT).

Step 1: Create Token
1. Visit https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: job-application-bot-deploy
4. Expiration: 90 days
5. Scopes: Check ONLY repo
6. Copy token immediately (cannot be retrieved later)

Step 2: Configure Git (One-Time Setup)
```bash
git config --global credential.helper osxkeychain
```

Step 3: Push Code
```bash
git push origin main
# Username: Micouwr
# Password: <paste your token>
# Token is now securely stored in macOS Keychain
```

---

## Building Standalone Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build cross-platform executable
python build_standalone.py
```

---

## Troubleshooting

"API key not found": Create .env file with GEMINI_API_KEY=your_key
"No active resume": Upload resume in "Resume Management" tab  
"Match analysis failed": Job description must be >= 100 characters  
"Git asks for password": See Token Management section above

---

## License

MIT License - See LICENSE file for details

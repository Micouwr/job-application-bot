# Job Application Bot

AI-Powered Resume Tailoring for IT/DevOps/AI Governance Roles

[Version: v2.2.0] [Python: 3.9+] [License: MIT]

---

## Overview

The Job Application Bot is an intelligent tool that helps you tailor your resume for specific job applications using Google's Gemini AI. By analyzing the job description and your resume, it creates customized versions that align with the position requirements while preserving all factual information from your original resume.

Key Features:
- AI-powered resume compatibility scoring
- Intelligent resume and cover letter tailoring
- Job description storage for future reference
- Professional PDF export capability
- Role-based customization for different position levels

---

## Quick Start

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

For PDF export functionality:
```bash
pip install reportlab
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

## How It Works

### 1. Analyze Job Compatibility
- Paste the job description (minimum 100 characters)
- Click "Analyze Match" to get your compatibility score
- Review detailed feedback on strengths and improvement areas

### 2. Tailor Your Application Materials
- For scores ≥70%, the "Start Tailoring" button becomes available
- AI generates a customized resume and cover letter
- All materials are automatically saved to the output folder

### 3. Manage and Export Your Documents
- View previously tailored applications in the "Tailored Documents" tab
- Export your materials as professionally formatted PDFs

---

## Configuration Options

### Minimum Match Threshold
Adjust the minimum compatibility score required to enable tailoring:
```python
# In config/settings.py
MIN_MATCH_THRESHOLD = 70  # Default: 70%
```

### Role Levels
Choose the appropriate role level for optimal tailoring:

1. **Standard**: Entry to mid-level positions (0-5 years)
2. **Senior**: Senior-level positions (5-10 years)
3. **Lead**: Lead positions (8-15 years)
4. **Principal**: Principal/architect positions (12+ years)

Select the level that best matches the position requirements.

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

Common issues and solutions:

- "API key not found": Ensure .env file contains your GEMINI_API_KEY
- "No active resume": Upload and set a resume as active in the Resume Management tab
- "Match analysis failed": Job description must be at least 100 characters

---

## License

MIT License - See LICENSE file for details
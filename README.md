# Job Application Bot - AI-Powered, Fully Customizable

Your personal IT/DevOps/AI Governance job hunter.
Uses Gemini 2.5 Flash + external prompt templates to:
- Understand any job description (not just keyword spam)
- Generate perfectly tailored resumes & cover letters
- Auto-switch to senior/staff voice for Staff+ roles
- Let you edit prompts in plain text - no Python required

Fully open-source, local-first, zero tracking.

## Features

- AI-Powered Matching - understands context, not just regex
- One-click tailored resume + cover letter (Markdown output)
- External prompts - edit prompts/*.jinja2 to change tone, style, or strategy
- Senior voice auto-detect - sounds like a Staff+ engineer when needed
- 100% offline-capable (just needs your Gemini API key)
- No PII in repo - resume & keys stored in .env (gitignored)

## Quick Start

```bash
git clone https://github.com/Micouwr/job-application-bot.git
cd job-application-bot

# 1. Install
pip install -r requirements.txt

# 2. Set up your secrets & resume
cp .env.example .env
# Edit .env - add your GEMINI_API_KEY
# Edit resume.json - your real resume (gitignored)

# 3. Run
python main.py interactive
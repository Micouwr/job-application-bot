# Job Application Bot — AI-Powered, Manual-Only (100% Safe & Legal)

Your personal IT/DevOps/AI Governance job hunter.  
Uses **Gemini 2.5 Flash** + fully editable prompt templates to:
- Understand any job description with real context
- Generate perfectly tailored resumes + cover letters
- Auto-switch to **senior/staff voice** for Staff+ roles
- Never scrape job boards — manual entry only (no bans, no ToS violations)

Fully open-source, local-first, zero tracking.

## Features

- AI-Powered Matching — understands nuance, not just keywords
- One-click tailored resume + cover letter (Markdown + PDF export)
- External prompts — edit `prompts/*.jinja2` to change tone, style, or strategy
- Senior voice auto-detect — sounds like a Staff/Principal engineer when needed
- 100% offline-capable (just needs your Gemini API key)
- No PII in repo — resume & keys stored in `.env` (gitignored)
- No automated scraping — 100% safe and legal

## Quick Start

```bash
git clone https://github.com/Micouwr/job-application-bot.git
cd job-application-bot

# 1. Install
pip install -r requirements.txt

# 2. Set up your secrets & resume
cp .env.example .env
# Edit .env → add your GEMINI_API_KEY
# Edit resume.json → your real resume (gitignored)

# 3. Run
python main.py interactive    # CLI mode
# or
python app/gui.py             # Full GUI with history
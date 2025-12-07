# Job Application Bot — AI Job Hunter: Intelligence-Driven, Zero-Scraping Architecture

Your personal IT/DevOps/AI Governance job hunter.
Uses **Gemini 2.5 Flash** + fully editable prompt templates to:
* Understand job descriptions with real context
* Generate **accurately tailored** resumes + cover letters
* Auto switch to **senior/staff voice** for Staff+ roles
* Never scrape job boards — manual entry only (no bans, no ToS violations)

Fully open-source, local-first, zero tracking.

---

## Features

* AI-Powered Matching — uses contextual understanding, not just keywords
* One-click tailored resume + cover letter (Markdown + PDF export)
* External prompts — edit `prompts/*.jinja2` to change tone, style, or strategy
* Senior voice auto detect — uses Staff/Principal engineer tone when needed
* 100% offline-capable (just needs your Gemini API key)
* No PII in repo — resume & keys stored in `.env` (gitignored)
* No automated scraping — fully compliant with site terms

---

## Quick Start

1. Install core dependencies
`pip install -r requirements.txt`

2. Set up your secrets & resume
`cp .env.example .env`
Edit .env → add your **GEMINI_API_KEY**
Edit resume.json → your real resume (gitignored)

3. Run
`python main.py interactive` (CLI mode)
or
`python app/gui.py` (Full GUI with history)

---

### For Contributors / Developers

* Install test dependencies
`pip install -r requirements-dev.txt`
* Run tests
`pytest`

---

### How to Add Jobs (Safe & Legal)

* Paste job description directly in GUI or CLI
* Import from CSV/JSON (export from your tracker)
* Manual entry — no automated scraping

---

### Customize Prompts (Configuration)

Want specific tone or focus?
Just edit the text files in `prompts/`:
* `system.txt` — default humble expert voice
* `system_senior.txt` — staff/principal tone (auto-used for senior roles)
* `skill_extraction.jinja2` — control how skills are pulled
* `full_resume_tailor.jinja2` — full resume layout & emphasis
* `cover_letter.jinja2` — tone, length, structure

No code changes. No rebuild. Just edit → run.

---

## Requirements

* Python 3.9+
* Gemini API key (free tier works great — 1M tokens/day at `aistudio.google.com`)

---

## Project Status

**v1.0.0 — Stable Release**
* Gemini 2.5 Flash locked
* External prompts
* Senior voice detection
* Threaded GUI
* No scraping

---

## License

**MIT License.** This means the project is open-source and allows for use, modification, distribution, and commercial use, provided the original copyright notice and license text are included.

---

## Development Status

Built by @Micouwr as an independent project in 2025.

# job-application-bot
Automated job application system for IT Infrastructure roles

# 🤖 Job Application Bot

Automated job application system that finds, matches, and tailors applications for IT Infrastructure positions.

**Built for:** Ryan Micou - Senior IT Infrastructure Architect  
**Focus:** IT Infrastructure, Help Desk Leadership, AI Governance, Cloud Architecture

---

## ✨ Features

- ✅ **Job Matching** - Scores jobs against your resume (80%+ threshold)
- ✅ **AI Tailoring** - Generates customized resumes & cover letters (no fabrication)
- ✅ **Application Tracking** - SQLite database tracks everything
- ✅ **Manual Control** - Human review before any submission
- ✅ **Complete Audit Trail** - Every change is logged

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Clone or download this repository
cd job-application-bot

# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers (for future scraping)
playwright install chromium
```

### 2. Configure API Key

```bash
# Copy .env template and add your API key
cp .env.example .env

# Edit .env and add your Anthropic API key
# Get one from: https://console.anthropic.com/
```

Edit `.env` file:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### 3. Run Interactive Mode

```bash
python main.py --interactive
```

Follow the prompts to add jobs manually!

---

## 📖 Usage

### Interactive Mode (Recommended for Start)

```bash
python main.py --interactive
```

This will prompt you to add jobs one by one:
- Job title
- Company name  
- Job URL
- Location
- Full job description

The bot will then:
1. Match each job against your resume
2. Tailor applications for high matches (≥80%)
3. Save everything to database and files

### Review Pending Applications

```bash
python main.py --review
```

Shows all applications ready for review with match scores and changes made.

### View Statistics

```bash
python main.py --stats
```

### Using as Python Library

```python
from main import JobApplicationBot

bot = JobApplicationBot()

# Add a job
bot.add_manual_job(
    title="Senior IT Infrastructure Architect",
    company="Tech Corp",
    url="https://linkedin.com/jobs/123456",
    description="Looking for senior architect with cloud and AI experience...",
    location="Louisville, KY (Remote)"
)

# Process it
bot.run_pipeline()

# Review results
bot.review_pending()
```

---

## 📁 Project Structure

```
job-application-bot/
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration and resume data
├── data/
│   └── job_applications.db  # SQLite database (created on first run)
├── logs/
│   └── job_application.log  # Application logs
├── output/
│   ├── resumes/            # Tailored resumes saved here
│   └── cover_letters/      # Cover letters saved here
├── main.py                 # Main application
├── scraper.py              # Job scraper (manual entry for now)
├── matcher.py              # Job matching engine
├── tailor.py               # AI-powered tailoring
├── database.py             # Database operations
├── requirements.txt        # Python dependencies
├── .env                    # API keys (DO NOT COMMIT!)
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

---

## ⚙️ Configuration

Edit `.env` file to customize:

```bash
# Your Anthropic API Key (REQUIRED)
ANTHROPIC_API_KEY=your_key_here

# Job Search Settings
JOB_LOCATION=Louisville, KY
MAX_JOBS_PER_PLATFORM=50
MATCH_THRESHOLD=0.80

# Your Contact Info
YOUR_NAME=William Ryan Micou
YOUR_EMAIL=micouwr2025@gmail.com
YOUR_PHONE=(502) 777 7526
```

Edit `config/settings.py` to update:
- Resume data (skills, experience, certifications)
- Job search keywords
- Matching algorithm weights
- AI model settings

---

## 🎯 How It Works

### 1. Job Matching Algorithm

**Scoring Formula:**
```
Match Score = 0.4 × Skills Match
            + 0.4 × Experience Relevance  
            + 0.2 × Keyword Match
            × Experience Level Multiplier
```

**Example:**
- Job mentions: AWS, Help Desk Leadership, AI Governance, Python
- You have: All of those skills ✓
- **Skills Score:** 95%
- **Experience Score:** 85% (relevant roles found)
- **Keyword Score:** 70% (good keyword density)
- **Final Match:** 85% → **APPLY!**

### 2. AI Tailoring (No Fabrication!)

The AI **ONLY**:
- ✅ Reorders achievements (relevant ones first)
- ✅ Adjusts summary emphasis
- ✅ Prioritizes matching skills
- ✅ Expands context on relevant experience

It **NEVER**:
- ❌ Adds new skills
- ❌ Creates fake achievements
- ❌ Changes dates or companies
- ❌ Invents certifications

### 3. Application Tracking

Everything is saved to SQLite database:
- All scraped/added jobs
- Match scores and analysis
- Tailored resumes and cover letters
- Application status (pending → applied → interview)
- Complete activity log

---

## 📊 Database Schema

Query the database directly:

```bash
# Open database
sqlite3 data/job_applications.db

# View all high matches
SELECT title, company, match_score 
FROM jobs 
WHERE match_score >= 0.80 
ORDER BY match_score DESC;

# View pending applications
SELECT j.title, j.company, a.status 
FROM jobs j 
JOIN applications a ON j.id = a.job_id 
WHERE a.status = 'pending_review';
```

---

## 🔧 Troubleshooting

### "ANTHROPIC_API_KEY not found"

Make sure you:
1. Created `.env` file in project root
2. Added your API key: `ANTHROPIC_API_KEY=sk-ant-...`
3. API key is valid (test at https://console.anthropic.com/)

### "No jobs met the match threshold"

Try:
1. Lower threshold in `.env`: `MATCH_THRESHOLD=0.75`
2. Add more varied job descriptions
3. Check that job descriptions include skill keywords

### "Error tailoring resume"

Check:
1. API key is valid and has credits
2. Internet connection is working
3. Job description isn't empty

---

## 🚦 Next Steps

### Week 1: Get Started
- [x] Install dependencies
- [x] Configure API key
- [ ] Add 3-5 jobs interactively
- [ ] Review generated applications
- [ ] Submit your first application!

### Week 2: Expand
- [ ] Add 10+ more jobs
- [ ] Track application responses
- [ ] Refine match threshold
- [ ] Update resume data with new skills

### Week 3: Optimize
- [ ] Analyze which match scores → interviews
- [ ] Adjust tailoring prompts
- [ ] Add company research to cover letters
- [ ] Build automation for high matches (95%+)

---

## 📚 Tips for Success

### Finding Jobs to Add

**LinkedIn:**
1. Search for your target roles
2. Open interesting jobs
3. Copy URL, title, company, and full description
4. Add to bot with `--interactive` mode

**Indeed:**
1. Browse relevant positions
2. Copy job details
3. Add to bot

**Company Career Pages:**
1. Check companies you're interested in
2. Direct links often have better info
3. Add these too!

### Getting Better Matches

**Improve Your Resume Data:**
- Add all relevant skills to `config/settings.py`
- Include tool versions (Python 3.x, AWS Certified, etc.)
- Add recent certifications
- Update project descriptions

**Optimize Job Descriptions:**
- Copy FULL job descriptions (more text = better matching)
- Include requirements section
- Don't skip qualifications

### Reviewing Applications

**Before Approving:**
1. Read tailored resume - does it sound like you?
2. Check cover letter - is it compelling?
3. Review changes - nothing fabricated?
4. Verify all dates and companies are correct

**After Approval:**
1. Copy resume and cover letter from `output/` folder
2. Submit via company portal
3. Update status in database: `UPDATE applications SET status='applied' WHERE job_id='...'`

---

## 🤝 Contributing

This is a personal project for Ryan Micou, but feel free to:
- Fork for your own use
- Customize for different industries
- Add new features (automated scraping, interview prep, etc.)

---

## 📄 License

Personal use project. Feel free to adapt for your own job search.

---

## 📞 Questions?

Check:
1. This README
2. Code comments in each module
3. Logs in `logs/job_application.log`
4. Database: `sqlite3 data/job_applications.db`

---

**Good luck with your job search! 🚀**

Remember: This bot handles the busy work, but your skills and personality are what land the job. Always add your personal touch before submitting!

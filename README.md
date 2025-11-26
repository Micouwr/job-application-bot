# 🤖 Job Application Bot - AI-Powered Application Automation

**Standalone Desktop Application** | **AI Model:** Gemini 2.5 Flash | **SDK:** Google GenAI (2025 Standard)

Automated job application system with **full GUI** that finds, matches, and tailors applications for IT Infrastructure roles using Google's Gemini AI. Built with Tkinter for cross-platform desktop deployment.

---

## ✨ Features

### 🖥️ **Full Desktop GUI Interface**
- **Tabbed Interface:** Tailor, Resume Management, View Jobs, Statistics
- **Drag & Drop Resume Upload:** Multiple resume version support
- **Real-time Preview:** See tailored outputs instantly
- **Progress Indicators:** Status bar with live updates
- **Cross-platform:** Works on Windows, macOS, Linux

### 🤖 **AI-Powered Automation**
- **Intelligent Job Matching:** 80%+ threshold with fuzzy logic and weighted skills
- **Resume Tailoring:** No fabrication - only reorders and emphasizes existing content
- **Cover Letter Generation:** Custom letters based on job requirements
- **Token Management:** tiktoken prevents API overflow
- **Response Caching:** Reduces API costs and latency

### 💾 **Data Management**
- **Multiple Resumes:** Upload, select, delete resume versions
- **SQLite Database:** Full ORM with soft deletes and audit trails
- **Application Tracking:** Complete lifecycle management
- **Export/Import:** CSV/JSON support for job lists
- **Automatic Backups:** Timestamped database backups

### 🛡️ **Enterprise Reliability**
- **Custom Exceptions:** MaxRetriesExceeded, JobNotFoundError
- **Exponential Backoff:** For API calls and user prompts
- **Size Validation:** Prevents oversized fields from crashing
- **Connection Pooling:** SQLAlchemy with pre-ping verification
- **User-Agent Rotation:** Avoids bot detection

---

## 🚀 Quick Start (GUI Mode)

### 1. Download & Install
**Standalone Executable (Recommended):**
- Download `JobApplicationBot_v2.0.exe` (Windows) or `JobApplicationBot.app` (macOS) from [Releases](https://github.com/Micouwr/job-application-bot/releases)

**Or Run from Source:**
```bash
git clone https://github.com/Micouwr/job-application-bot.git
cd job-application-bot
pip install -r requirements.txt

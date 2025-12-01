# 🤖 Job Application Bot - AI-Powered Application Automation

**Standalone Desktop Application** | **AI Model:** Gemini 2.5 Flash | **SDK:** Google GenAI (2025 Standard)

Automated job application system with **full GUI** that finds, matches, and tailors applications for IT Infrastructure roles using Google's Gemini AI. Built with Tkinter for cross-platform desktop deployment.

---

## ✨ Features

### 🖥️ **Full Desktop GUI Interface**
- **Tabbed Interface:** Tailor, Resume Management, View Jobs, Statistics
- **Resume Upload:** Upload and manage multiple resume versions.
- **Real-time Preview:** See tailored outputs instantly.
- **Progress Indicators:** Status bar with live updates.
- **Cross-platform:** Works on Windows, macOS, Linux.

### 🤖 **AI-Powered Automation**
- **Intelligent Job Matching:** Sophisticated algorithm with fuzzy logic and weighted skills.
- **Resume Tailoring:** Reorders and emphasizes existing content from your resume without fabrication.
- **Cover Letter Generation:** Creates custom cover letters based on the job requirements.

### 💾 **Data Management**
- **Multiple Resumes:** Upload, select, and delete different resume versions.
- **SQLite Database:** Uses a robust SQLite database with a full ORM.
- **Application Tracking:** Manage the entire lifecycle of your job applications.
- **Export/Import:** Export your job list to CSV/JSON.
- **Automatic Backups:** Creates timestamped backups of your application database.

### 🛡️ **Enterprise Reliability**
- **Custom Exceptions:** Handles specific errors like `JobNotFoundError`.
- **Connection Pooling:** Uses SQLAlchemy for efficient database connection management.
- **User-Agent Rotation:** Rotates User-Agents to avoid bot detection during scraping.

---

## 🚀 Quick Start (Running from Source)

### 1. Clone the Repository
```bash
git clone https://github.com/Micouwr/job-application-bot.git
cd job-application-bot
```

### 2. Set Up Your Environment
Create a `.env` file in the root of the project by copying the example file:
```bash
cp .env_example .env
```
Now, open the `.env` file and add your Google Gemini API key. You must also fill in your personal information (name, email, etc.).

### 3. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 4. Run the Application
Launch the desktop GUI:
```bash
python gui_app.py
```

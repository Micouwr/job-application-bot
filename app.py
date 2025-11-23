from flask import Flask, request
import json
import os
from main import JobApplicationBot
from database import JobDatabase
from config.settings import JOB_LOCATION

app = Flask(__name__)
bot = JobApplicationBot()

@app.route('/')
def index():
    """Serve the web interface"""
    with open('web_interface.html', 'r') as f:
        return f.read()

@app.route('/api/status')
def status():
    """Get bot status"""
    try:
        db = JobDatabase()
        stats = db.get_statistics()
        return json.dumps(stats)
    except Exception:
        return json.dumps({"status": "ready"})

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get pending jobs"""
    try:
        db = JobDatabase()
        jobs = db.get_pending_reviews()
        return json.dumps(jobs)
    except Exception:
        return json.dumps([])

@app.route('/api/add_job', methods=['POST'])
def add_job():
    """Add a job manually via API"""
    title = request.form.get("title", "")
    company = request.form.get("company", "Unknown")   # optional
    url = request.form.get("url", "")                  # optional
    description = request.form.get("description", "")
    location = request.form.get("location", JOB_LOCATION)

    job = bot.add_manual_job(title, company, url, description, location)
    bot.run_pipeline(manual_jobs=[job])

        return jsonify({
        "status": "success",
        "message": f"Job '{title}' added and processed!",
        "job": job
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

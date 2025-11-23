from flask import Flask, render_template_string
import json
import os
from main import JobApplicationBot
from database import JobDatabase

app = Flask(__name__)

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
    except:
        return json.dumps({"status": "ready"})

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get pending jobs"""
    try:
        db = JobDatabase()
        jobs = db.get_pending_reviews()
        return json.dumps(jobs)
    except:
        return json.dumps([])

if __name__ == '__main__':
    app.run(debug=True, port=5000)

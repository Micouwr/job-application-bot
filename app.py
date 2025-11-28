import json
import logging
from threading import Thread
from flask import Flask, request, jsonify # jsonify is necessary for structured JSON responses

from config.settings import JOB_LOCATION
# Assuming database.py provides JobDatabase and main.py provides JobApplicationBot
from database import JobDatabase 
from main import JobApplicationBot 

# Setup logging for the Flask app
logger = logging.getLogger(__name__)
# The overall logging level is set in config/settings.py and applied in main.py, 
# but setting a local level ensures visibility for Flask context errors.
logger.setLevel(logging.INFO) 

app = Flask(__name__)
# Initialize the bot which holds the configuration and resume data
bot = JobApplicationBot()


@app.route("/")
def index():
    """Serve the web interface (Assumes web_interface.html exists)"""
    try:
        # Note: In a production Flask app, 'render_template' or 'send_static_file' is preferred, 
        # but reading the file directly works for simple demos.
        with open("web_interface.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        # Simple error message if the HTML file is missing
        return "<h1>Error: web_interface.html not found.</h1>", 500


@app.route("/api/status")
def status():
    """Get bot status and database statistics"""
    try:
        db = JobDatabase()
        db.connect()
        stats = db.get_statistics()
        db.close()
        
        # Check if a pipeline is currently running (based on bot status in main.py)
        stats["pipeline_running"] = bot.is_pipeline_running() 
        stats["location"] = JOB_LOCATION
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        # Return a 500 status code for server errors
        return jsonify({"status": "error", "error": str(e), "pipeline_running": False}), 500


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """Get pending jobs for review (those with a high match score but no action yet)"""
    try:
        db = JobDatabase()
        db.connect()
        jobs = db.get_pending_reviews()
        db.close()
        return jsonify(jobs)
    except Exception as e:
        logger.error(f"Failed to retrieve pending jobs: {e}")
        return jsonify({"status": "error", "message": "Database access failed"}), 500


@app.route("/api/add_job", methods=["POST"])
def add_job():
    """
    Add a job manually via API and start the pipeline asynchronously.
    Running the pipeline in a thread prevents the web server from blocking.
    """
    # Accept data from JSON body or form data
    data = request.get_json(silent=True) or request.form
    
    title = data.get("title", "")
    company = data.get("company", "Unknown")
    url = data.get("url", "")
    description = data.get("description", "")
    location = data.get("location", JOB_LOCATION)

    if not title or not description:
        return jsonify({"status": "error", "message": "Job title and description are required."}), 400

    try:
        # 1. Add the job to the database (synchronous operation)
        job = bot.add_manual_job(title, company, url, description, location)
        
        # 2. Start the resource-intensive pipeline in a background thread
        pipeline_thread = Thread(
            target=bot.run_pipeline, 
            # We don't need a callback here as status is checked via /api/status
            kwargs={'manual_jobs': [job], 'dry_run': False}
        )
        pipeline_thread.start()
        
        logger.info(f"Job '{title}' added and pipeline started in background thread.")

        return jsonify(
            {
                "status": "success",
                "message": f"Job '{title}' added and processing started in background.",
                "job_id": job.get('id'), # Return the DB ID
            }
        )
    except Exception as e:
        logger.error(f"Error processing manual job addition: {e}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    # Ensure that any logging configuration in main.py is applied before this point, 
    # or keep this simple for local development.
    app.run(debug=True, port=5000)
"""
Database module for job application tracking.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)


class JobDatabase:
    """
    Handles all interactions with the SQLite database for the Job Application Bot.

    This class provides methods for initializing the database, inserting and updating jobs,
    saving applications, and retrieving data for review and statistics.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initializes the JobDatabase.

        Args:
            db_path: The path to the SQLite database file. If not provided,
                     it uses the default path from the settings.
        """
        self.db_path = db_path or DATABASE_PATH
        self.conn: Optional[sqlite3.Connection] = None
        self.init_database()

    def init_database(self) -> None:
        """Initializes the database with all the required tables."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        cursor = self.conn.cursor()

        # Jobs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                description TEXT,
                requirements TEXT,
                url TEXT,
                salary TEXT,
                job_type TEXT,
                experience_level TEXT,
                source TEXT,
                scraped_at TIMESTAMP,
                match_score REAL,
                status TEXT DEFAULT 'new',
                raw_data TEXT
            )
        """
        )

        # Match details
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS match_details (
                job_id TEXT PRIMARY KEY,
                matched_skills TEXT,
                missing_skills TEXT,
                relevant_experience TEXT,
                strengths TEXT,
                gaps TEXT,
                reasoning TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """
        )

        # Applications
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                tailored_resume TEXT,
                cover_letter TEXT,
                changes_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_at TIMESTAMP,
                status TEXT DEFAULT 'pending_review',
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """
        )

        # Interviews
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                interview_date TIMESTAMP,
                interview_type TEXT,
                interviewer_name TEXT,
                notes TEXT,
                outcome TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """
        )

        # Activity log
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def insert_job(self, job: Dict) -> bool:
        """
        Inserts a new job listing into the database.

        Args:
            job: A dictionary containing the job details.

        Returns:
            True if the insertion was successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO jobs 
                (id, title, company, location, description, requirements, url, 
                 salary, job_type, experience_level, source, scraped_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    job["id"],
                    job["title"],
                    job["company"],
                    job.get("location"),
                    job.get("description"),
                    job.get("requirements"),
                    job.get("url"),
                    job.get("salary"),
                    job.get("job_type"),
                    job.get("experience_level"),
                    job["source"],
                    job.get("scraped_at", datetime.now().isoformat()),
                    json.dumps(job),
                ),
            )
            self.conn.commit()
            self.log_activity(job["id"], "job_added", f"Added: {job['title']}")
            return True
        except Exception as e:
            logger.error(f"Error inserting job: {e}")
            return False

    def update_match_score(self, job_id: str, match_result: Dict) -> bool:
        """
        Updates a job with its match score and other details.

        Args:
            job_id: The ID of the job to update.
            match_result: A dictionary containing the match results.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            cursor = self.conn.cursor()

            # Update job
            cursor.execute(
                """
                UPDATE jobs 
                SET match_score = ?, status = ?
                WHERE id = ?
            """,
                (
                    match_result["match_score"],
                    "matched" if match_result["match_score"] >= 0.80 else "low_match",
                    job_id,
                ),
            )

            # Insert match details
            cursor.execute(
                """
                INSERT OR REPLACE INTO match_details
                (job_id, matched_skills, missing_skills, relevant_experience,
                 strengths, gaps, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    job_id,
                    json.dumps(match_result.get("matched_skills", [])),
                    json.dumps(match_result.get("missing_skills", [])),
                    json.dumps(match_result.get("relevant_experience", [])),
                    json.dumps(match_result.get("strengths", [])),
                    json.dumps(match_result.get("gaps", [])),
                    match_result.get("reasoning", ""),
                ),
            )

            self.conn.commit()

            if match_result["match_score"] >= 0.80:
                self.log_activity(
                    job_id,
                    "high_match",
                    f"Match: {match_result['match_score']*100:.1f}%",
                )
            return True
        except Exception as e:
            logger.error(f"Error updating match score: {e}")
            return False

    def save_application(
        self, job_id: str, resume: str, cover_letter: str, changes: List[str]
    ) -> bool:
        """
        Saves a tailored application to the database.

        Args:
            job_id: The ID of the job the application is for.
            resume: The tailored resume text.
            cover_letter: The tailored cover letter text.
            changes: A list of changes made to the resume.

        Returns:
            True if the application was saved successfully, False otherwise.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO applications
                (job_id, tailored_resume, cover_letter, changes_summary, status)
                VALUES (?, ?, ?, ?, ?)
            """,
                (job_id, resume, cover_letter, json.dumps(changes), "pending_review"),
            )

            self.conn.commit()
            self.log_activity(
                job_id, "application_prepared", "Tailored application ready"
            )
            return True
        except Exception as e:
            logger.error(f"Error saving application: {e}")
            return False

    def update_status(
        self, job_id: str, status: str, notes: Optional[str] = None
    ) -> bool:
        """
        Updates the status of an application.

        Args:
            job_id: The ID of the job to update.
            status: The new status of the application.
            notes: Optional notes to add to the application.

        Returns:
            True if the status was updated successfully, False otherwise.
        """
        try:
            cursor = self.conn.cursor()

            # Update application
            cursor.execute(
                """
                UPDATE applications
                SET status = ?,
                    applied_at = CASE WHEN ? = 'applied' THEN CURRENT_TIMESTAMP ELSE applied_at END,
                    notes = COALESCE(?, notes)
                WHERE job_id = ?
            """,
                (status, status, notes, job_id),
            )

            # Update job status
            cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))

            self.conn.commit()
            self.log_activity(job_id, "status_change", f"Status: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False

    def get_pending_reviews(self) -> List[Dict]:
        """
        Gets all applications that are pending review.

        Returns:
            A list of dictionaries, where each dictionary represents an application.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT j.*, a.tailored_resume, a.cover_letter, a.changes_summary,
                   m.matched_skills, m.missing_skills, m.strengths, m.gaps
            FROM jobs j
            JOIN applications a ON j.id = a.job_id
            LEFT JOIN match_details m ON j.id = m.job_id
            WHERE a.status = 'pending_review'
            ORDER BY j.match_score DESC
        """
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict:
        """
        Gets statistics about the job applications.

        Returns:
            A dictionary containing the statistics.
        """
        cursor = self.conn.cursor()

        stats: Dict[str, any] = {}

        cursor.execute("SELECT COUNT(*) FROM jobs")
        stats["total_jobs"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 0.80")
        stats["high_matches"] = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
        stats["by_status"] = dict(cursor.fetchall())

        cursor.execute(
            "SELECT AVG(match_score) FROM jobs WHERE match_score IS NOT NULL"
        )
        avg = cursor.fetchone()[0]
        stats["avg_match_score"] = round(avg, 3) if avg else 0

        return stats

    def log_activity(self, job_id: str, action: str, details: str) -> None:
        """
        Logs an activity to the database.

        Args:
            job_id: The ID of the job the activity is related to.
            action: The type of action that was performed.
            details: A description of the activity.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO activity_log (job_id, action, details)
                VALUES (?, ?, ?)
            """,
                (job_id, action, details),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error logging activity: {e}")

    def close(self) -> None:
        """Closes the database connection."""
        if self.conn:
            self.conn.close()

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
import time

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Handles SQLite database connections and operations for logging job matching
    and application tailoring history.
    """
    DB_NAME = "history.db"

    def __init__(self) -> None:
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Creates the necessary tables if they do not exist."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()
            
            # Table to store history of analyses and tailoring
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL, 
                    job_title TEXT,
                    resume_file TEXT,
                    match_score REAL,
                    result_summary TEXT, 
                    created_at TEXT
                )
            """)
            
            # Table to store the full output of a tailoring run
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tailoring_results (
                    history_id INTEGER PRIMARY KEY,
                    tailored_resume TEXT NOT NULL,
                    cover_letter TEXT NOT NULL,
                    changes_made TEXT, -- Stored as a JSON string or delimited string
                    FOREIGN KEY (history_id) REFERENCES history(id)
                )
            """)
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error("SQLite database initialization error: %s", e)
        finally:
            if conn:
                conn.close()

    def log_analysis(self, job_title: str, resume_file: str, score: float) -> None:
        """Logs a single matching analysis run."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT INTO history 
                (timestamp, action, job_title, resume_file, match_score, result_summary, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (now_iso, "MATCH_ANALYSIS", job_title, resume_file, score, f"Score: {score:.2f}", now_iso))
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Error logging analysis: %s", e)
        finally:
            if conn:
                conn.close()

    def log_tailoring_result(self, job_title: str, resume_file: str, results: Dict[str, Any]) -> None:
        """
        Logs the full tailoring run (history record + detailed results).
        
        Args:
            job_title: The title of the job.
            resume_file: The identifier for the resume used.
            results: The dictionary containing 'resume_text', 'cover_letter', and 'changes'.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()
            now_iso = datetime.utcnow().isoformat()
            
            # 1. Log the general history event first
            cursor.execute("""
                INSERT INTO history 
                (timestamp, action, job_title, resume_file, result_summary, created_at) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (now_iso, "TAILOR_RUN", job_title, resume_file, "Tailoring run complete.", now_iso))
            
            history_id = cursor.lastrowid # Get the ID of the newly inserted history record

            # Convert the list of changes into a simple delimited string for storage
            changes_str = "\n".join(results.get("changes", []))

            # 2. Log the detailed tailoring results
            cursor.execute("""
                INSERT INTO tailoring_results 
                (history_id, tailored_resume, cover_letter, changes_made) 
                VALUES (?, ?, ?, ?)
            """, (history_id, results["resume_text"], results["cover_letter"], changes_str))
            
            conn.commit()
            logger.info("Tailoring run logged successfully with history ID: %s", history_id)
        except sqlite3.Error as e:
            logger.error("Error logging tailoring result: %s", e)
            if conn:
                conn.rollback() # Rollback if logging failed
        finally:
            if conn:
                conn.close()

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieves all general history records."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            conn.row_factory = sqlite3.Row # Allows accessing columns by name
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM history ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Error retrieving history: %s", e)
            return []
        finally:
            if conn:
                conn.close()
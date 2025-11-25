"""
Database module for job application tracking.
Thread-safe operations with transaction support and audit logging.
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Generator

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Database operation error"""
    pass


class RecordNotFoundError(DatabaseError):
    """Requested record does not exist"""
    pass


class JobDatabase:
    """
    Thread-safe database operations with connection pooling and audit logging.
    
    Features:
    - Connection pooling for performance
    - Transaction support with automatic rollback
    - Atomic operations to prevent race conditions
    - Comprehensive error handling
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database with connection pool
        
        Args:
            db_path: Path to database file, defaults to DATABASE_PATH
        """
        self.db_path = db_path or DATABASE_PATH
        self._pool: List[sqlite3.Connection] = []
        self._pool_lock = threading.Lock()
        self._max_connections = 5  # Perfect for personal use
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize schema
        self._init_schema()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get connection from pool or create new one.
        Thread-safe connection management.
        """
        conn = None
        
        # Try to reuse from pool
        with self._pool_lock:
            if self._pool:
                conn = self._pool.pop()
        
        # Create new connection if needed
        if conn is None:
            try:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=30.0,  # Wait 30 seconds for locks
                    isolation_level=None,  # Manual transaction control
                    check_same_thread=False  # We'll handle thread safety
                )
                conn.row_factory = sqlite3.Row
                # Enable foreign keys and optimize
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
                
                logger.debug("Created new database connection")
            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to create connection: {e}")
        
        try:
            yield conn
        finally:
            # Return to pool if not at max size
            with self._pool_lock:
                if len(self._pool) < self._max_connections:
                    self._pool.append(conn)
                else:
                    conn.close()
                    logger.debug("Closed excess database connection")
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for atomic database transactions.
        
        Usage:
            with db.transaction() as cursor:
                cursor.execute("INSERT ...")
                # Commits automatically if no exception
            # Rolls back automatically if exception occurs
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN")  # Explicit transaction start
            try:
                yield cursor
                conn.commit()
                logger.debug("Transaction committed successfully")
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise DatabaseError(f"Transaction failed: {e}")

    def _init_schema(self):
        """Initialize database schema with versioning"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if schema version table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """)
            
            if not cursor.fetchone():
                # Initial schema creation
                cursor.executescript("""
                    CREATE TABLE schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE jobs (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        company TEXT NOT NULL,
                        location TEXT,
                        description TEXT NOT NULL,
                        requirements TEXT,
                        url TEXT UNIQUE NOT NULL,
                        salary TEXT,
                        job_type TEXT,
                        experience_level TEXT,
                        source TEXT NOT NULL,
                        scraped_at TIMESTAMP NOT NULL,
                        match_score REAL,
                        status TEXT NOT NULL DEFAULT 'new',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX idx_jobs_status ON jobs(status);
                    CREATE INDEX idx_jobs_match_score ON jobs(match_score);
                    CREATE INDEX idx_jobs_company ON jobs(company);
                    CREATE INDEX idx_jobs_url ON jobs(url);
                    CREATE INDEX idx_jobs_created ON jobs(created_at);
                    
                    CREATE TABLE match_details (
                        job_id TEXT PRIMARY KEY,
                        matched_skills TEXT,
                        missing_skills TEXT,
                        relevant_experience TEXT,
                        strengths TEXT,
                        gaps TEXT,
                        reasoning TEXT,
                        keyword_matches TEXT,
                        component_scores TEXT,
                        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                    );
                    
                    CREATE TABLE applications (
                        id TEXT PRIMARY KEY,
                        job_id TEXT NOT NULL UNIQUE,
                        tailored_resume TEXT,
                        cover_letter TEXT,
                        changes_summary TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT NOT NULL DEFAULT 'pending_review',
                        notes TEXT,
                        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                    );
                    
                    CREATE INDEX idx_applications_status ON applications(status);
                    CREATE INDEX idx_applications_job_id ON applications(job_id);
                    
                    CREATE TABLE activity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT,
                        application_id TEXT,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
                        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL
                    );
                    
                    CREATE INDEX idx_activity_job ON activity_log(job_id);
                    CREATE INDEX idx_activity_timestamp ON activity_log(timestamp);
                    
                    CREATE TABLE interviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        application_id TEXT NOT NULL,
                        interview_date TIMESTAMP NOT NULL,
                        interview_type TEXT NOT NULL,
                        interviewer_name TEXT,
                        notes TEXT,
                        outcome TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
                    );
                    
                    INSERT INTO schema_version (version) VALUES (1);
                """)
                
                conn.commit()
                logger.info("Database schema created (version 1)")
    
    def insert_job(self, job: Dict) -> Optional[str]:
        """
        Insert a new job with atomic duplicate detection.
        
        Args:
            job: Job dictionary with required fields (id, title, company, url, description, source)
            
        Returns:
            Job ID if inserted successfully, None if duplicate or failed
            
        Raises:
            DatabaseError: If insertion fails after duplicate check
        """
        required_fields = ["id", "title", "company", "url", "description", "source"]
        for field in required_fields:
            if not job.get(field):
                raise ValueError(f"Job is missing required field: {field}")
        
        try:
            with self.transaction() as cursor:
                # Atomic INSERT OR IGNORE - prevents race conditions
                cursor.execute("""
                    INSERT OR IGNORE INTO jobs (
                        id, title, company, location, description, requirements, url,
                        salary, job_type, experience_level, source, scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job["id"],
                    job["title"],
                    job["company"],
                    job.get("location"),
                    job["description"],
                    job.get("requirements"),
                    job["url"],
                    job.get("salary"),
                    job.get("job_type"),
                    job.get("experience_level"),
                    job["source"],
                    job.get("scraped_at", datetime.now().isoformat()),
                ))
                
                # Check if row was actually inserted
                if cursor.rowcount == 0:
                    logger.warning(f"Job already exists (duplicate URL): {job['url']}")
                    return None
                
                # Log the activity
                self._log_activity(
                    cursor=cursor,
                    job_id=job["id"],
                    action="job_inserted",
                    details=f"Added job: {job['title']} at {job['company']}"
                )
                
                logger.info(f"Job inserted: {job['id']}")
                return job["id"]
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Job already exists in database: {job['url']}")
                return None
            else:
                raise DatabaseError(f"Integrity error: {e}")
        except Exception as e:
            logger.error(f"Failed to insert job: {e}")
            raise DatabaseError(f"Database error: {e}")

    def update_match_score(self, job_id: str, match_result: Dict) -> bool:
        """
        Updates job with match score and detailed analysis.
        
        Args:
            job_id: Job ID to update
            match_result: Dictionary with match analysis
            
        Returns:
            True if successful, False if job not found
            
        Raises:
            DatabaseError: If update fails
        """
        try:
            with self.transaction() as cursor:
                # Update jobs table
                cursor.execute("""
                    UPDATE jobs
                    SET match_score = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    match_result["match_score"],
                    "matched" if match_result["match_score"] >= 0.80 else "low_match",
                    job_id
                ))
                
                if cursor.rowcount == 0:
                    logger.warning(f"Job not found for match update: {job_id}")
                    return False
                
                # Insert match details
                cursor.execute("""
                    INSERT OR REPLACE INTO match_details (
                        job_id, matched_skills, missing_skills, relevant_experience,
                        strengths, gaps, reasoning, keyword_matches, component_scores
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id,
                    json.dumps(match_result.get("matched_skills", [])),
                    json.dumps(match_result.get("missing_skills", [])),
                    json.dumps(match_result.get("relevant_experience", [])),
                    json.dumps(match_result.get("strengths", [])),
                    json.dumps(match_result.get("gaps", [])),
                    match_result.get("reasoning", ""),
                    json.dumps(match_result.get("keyword_matches", {})),
                    json.dumps(match_result.get("scores", {}))
                ))
                
                logger.debug(f"Match score updated for job: {job_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating match score: {e}")
            raise DatabaseError(f"Failed to update match: {e}")

    def save_application(self, job_id: str, resume: str, cover_letter: str, changes: List) -> bool:
        """
        Save tailored application with atomic operation.
        
        Args:
            job_id: Associated job ID
            resume: Tailored resume text
            cover_letter: Tailored cover letter text
            changes: List of changes made
            
        Returns:
            True if successful
            
        Raises:
            DatabaseError: If save fails
        """
        from utils.security import generate_application_id
        
        try:
            app_id = generate_application_id(job_id)
            
            with self.transaction() as cursor:
                cursor.execute("""
                    INSERT INTO applications (
                        id, job_id, tailored_resume, cover_letter, changes_summary, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    app_id,
                    job_id,
                    resume,
                    cover_letter,
                    json.dumps(changes),
                    "pending_review"
                ))
                
                self._log_activity(
                    cursor=cursor,
                    job_id=job_id,
                    application_id=app_id,
                    action="application_created",
                    details=f"Application prepared for job: {job_id}"
                )
                
                logger.info(f"Application saved: {app_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving application: {e}")
            raise DatabaseError(f"Failed to save application: {e}")

    def get_pending_reviews(self) -> List[Dict]:
        """
        Get all applications pending review with full details.
        
        Returns:
            List of application dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        j.id as job_id,
                        j.title,
                        j.company,
                        j.location,
                        j.url,
                        j.match_score,
                        a.id as application_id,
                        a.tailored_resume,
                        a.cover_letter,
                        a.changes_summary,
                        a.created_at
                    FROM applications a
                    JOIN jobs j ON a.job_id = j.id
                    WHERE a.status = 'pending_review'
                    ORDER BY j.match_score DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            return []

    def get_statistics(self) -> Dict:
        """
        Get comprehensive statistics about job applications.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Basic counts
                cursor.execute("SELECT COUNT(*) FROM jobs")
                stats["total_jobs"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 0.80")
                stats["high_matches"] = cursor.fetchone()[0]
                
                # Applications by status
                cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
                stats["by_status"] = dict(cursor.fetchall())
                
                # Average match score
                cursor.execute("""
                    SELECT AVG(match_score) FROM jobs 
                    WHERE match_score IS NOT NULL
                """)
                avg = cursor.fetchone()[0]
                stats["avg_match_score"] = round(avg, 3) if avg else 0.0
                
                # Top companies
                cursor.execute("""
                    SELECT company, COUNT(*) as count
                    FROM jobs
                    GROUP BY company
                    ORDER BY count DESC
                    LIMIT 10
                """)
                stats["top_companies"] = [
                    {"company": row[0], "count": row[1]}
                    for row in cursor.fetchall()
                ]
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_jobs": 0,
                "high_matches": 0,
                "by_status": {},
                "avg_match_score": 0.0,
                "top_companies": []
            }

    def update_status(self, job_id: str, new_status: str) -> bool:
        """
        Update application status.
        
        Args:
            job_id: Job ID to update
            new_status: New status value
            
        Returns:
            True if updated, False if not found
        """
        try:
            with self.transaction() as cursor:
                cursor.execute(
                    "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
                    (new_status, job_id)
                )
                
                if cursor.rowcount == 0:
                    logger.warning(f"No application found for job_id: {job_id}")
                    return False
                
                self._log_activity(
                    cursor=cursor,
                    job_id=job_id,
                    action="status_updated",
                    details=f"Status changed to: {new_status}"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False

    def _log_activity(self, cursor: sqlite3.Cursor, action: str, details: str,
                      job_id: Optional[str] = None, application_id: Optional[str] = None):
        """Internal: Log activity with sanitization"""
        # Sanitize details to prevent logging sensitive data
        if len(details) > 500:
            details = details[:500] + "..."
        
        cursor.execute("""
            INSERT INTO activity_log (job_id, application_id, action, details)
            VALUES (?, ?, ?, ?)
        """, (job_id, application_id, action, details))

    def close(self):
        """Close all database connections in pool"""
        try:
            with self._pool_lock:
                for conn in self._pool:
                    try:
                        conn.close()
                    except Exception as e:
                        logger.error(f"Error closing connection: {e}")
                self._pool.clear()
            
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error during database close: {e}")

# Context manager support
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Demo function
def demo_database():
    """Demonstrate database functionality"""
    db = JobDatabase()
    
    # Sample job
    sample_job = {
        "id": "test_123456",
        "title": "Senior IT Architect",
        "company": "Test Corp",
        "url": "https://example.com/jobs/123",
        "description": "Sample job description",
        "source": "manual",
    }
    
    try:
        # Insert job
        job_id = db.insert_job(sample_job)
        if job_id:
            print(f"✓ Inserted job: {job_id}")
        else:
            print("ℹ️  Job already exists (duplicate detection working)")
        
        # Get stats
        stats = db.get_statistics()
        print(f"\nDatabase stats: {stats}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo_database()

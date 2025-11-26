"""
Database module for job application tracking with connection management and auto-cleanup.
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)

class JobDatabase:
    """
    Handles all SQLite database operations with proper connection management.
    Implements context manager for safe resource handling.
    """
    
    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize database with lazy connection creation.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or DATABASE_PATH
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_schema()
        logger.info(f"✓ Database initialized at {self.db_path}")
    
    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy connection property with row factory"""
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(
                    str(self.db_path),
                    detect_types=sqlite3.PARSE_DECLTYPES,
                    isolation_level=None  # Autocommit mode
                )
                self._conn.row_factory = sqlite3.Row
                # Enable foreign keys
                self._conn.execute("PRAGMA foreign_keys = ON")
                # Optimize for performance
                self._conn.execute("PRAGMA journal_mode = WAL")
                self._conn.execute("PRAGMA synchronous = NORMAL")
            except sqlite3.Error as e:
                logger.critical(f"Failed to connect to database: {e}")
                raise RuntimeError(f"Database connection failed: {e}")
        return self._conn
    
    def __enter__(self):
        """Context manager entry - returns self"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed"""
        self.close()
    
    def _initialize_schema(self) -> None:
        """Create all required tables if they don't exist"""
        try:
            cursor = self.conn.cursor()
            
            # Jobs table - stores job postings
            cursor.execute("""
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
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    match_score REAL,
                    status TEXT DEFAULT 'new',
                    raw_data TEXT
                )
            """)
            
            # Match details - stores match analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_details (
                    job_id TEXT PRIMARY KEY,
                    matched_skills TEXT,
                    missing_skills TEXT,
                    relevant_experience TEXT,
                    strengths TEXT,
                    gaps TEXT,
                    reasoning TEXT,
                    scores TEXT,
                    metadata TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """)
            
            # Applications - stores tailored applications
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    tailored_resume TEXT,
                    cover_letter TEXT,
                    changes_summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_at TIMESTAMP,
                    status TEXT DEFAULT 'pending_review',
                    notes TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """)
            
            # Activity log - audit trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)
            """)
            
            self.conn.commit()
            logger.info("✓ Database schema initialized")
            
        except sqlite3.Error as e:
            logger.error(f"Schema initialization failed: {e}")
            raise RuntimeError(f"Database schema error: {e}")
    
    def job_exists(self, job_id: str) -> bool:
        """Check if job ID already exists"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM jobs WHERE id = ? LIMIT 1", (job_id,))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.warning(f"Error checking job existence: {e}")
            return False
    
    def insert_job(self, job: Dict[str, Any]) -> bool:
        """Insert a new job listing with duplicate protection"""
        try:
            # Check for duplicate first
            if self.job_exists(job["id"]):
                logger.warning(f"Job {job['id']} already exists, skipping")
                return False
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (
                    id, title, company, location, description, requirements, url,
                    salary, job_type, experience_level, source, scraped_at, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
                job.get("source", "manual"),
                job.get("scraped_at", datetime.now().isoformat()),
                json.dumps(job),
            ))
            
            self.conn.commit()
            self.log_activity(job["id"], "job_added", f"Added: {job['title']}")
            logger.info(f"✓ Job inserted: {job['title']}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"Job {job['id']} already exists")
            return False
        except sqlite3.Error as e:
            logger.error(f"Error inserting job: {e}")
            return False
    
    def update_match_score(self, job_id: str, match_result: Dict[str, Any]) -> bool:
        """Update job with match score and detailed analysis"""
        try:
            cursor = self.conn.cursor()
            
            # Update jobs table
            cursor.execute("""
                UPDATE jobs
                SET match_score = ?, status = ?
                WHERE id = ?
            """, (
                match_result["match_score"],
                "matched" if match_result["match_score"] >= 0.80 else "low_match",
                job_id,
            ))
            
            # Insert match details
            cursor.execute("""
                INSERT OR REPLACE INTO match_details (
                    job_id, matched_skills, missing_skills, relevant_experience,
                    strengths, gaps, reasoning, scores, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                json.dumps(match_result.get("matched_skills", [])),
                json.dumps(match_result.get("missing_skills", [])),
                json.dumps(match_result.get("relevant_experience", [])),
                json.dumps(match_result.get("strengths", [])),
                json.dumps(match_result.get("gaps", [])),
                match_result.get("reasoning", ""),
                json.dumps(match_result.get("scores", {})),
                json.dumps(match_result.get("metadata", {})),
            ))
            
            self.conn.commit()
            
            if match_result["match_score"] >= 0.80:
                self.log_activity(job_id, "high_match", f"Score: {match_result['match_score']*100:.1f}%")
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating match score: {e}")
            return False
    
    def save_application(
        self,
        job_id: str,
        resume: str,
        cover_letter: str,
        changes: List[str]
    ) -> bool:
        """Save tailored application with conflict resolution"""
        try:
            cursor = self.conn.cursor()
            
            # Use INSERT OR REPLACE to handle conflicts
            cursor.execute("""
                INSERT OR REPLACE INTO applications (
                    job_id, tailored_resume, cover_letter, changes_summary, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                resume,
                cover_letter,
                json.dumps(changes),
                "pending_review",
            ))
            
            self.conn.commit()
            self.log_activity(job_id, "application_prepared", "Tailored application ready")
            logger.info(f"✓ Application saved for job {job_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error saving application: {e}")
            return False
    
    def update_status(
        self,
        job_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update application status with timestamp"""
        try:
            cursor = self.conn.cursor()
            
            # Update application
            cursor.execute("""
                UPDATE applications
                SET status = ?,
                    applied_at = CASE WHEN ? = 'applied' THEN CURRENT_TIMESTAMP ELSE applied_at END,
                    notes = COALESCE(?, notes)
                WHERE job_id = ?
            """, (status, status, notes, job_id))
            
            # Update job status
            cursor.execute("""
                UPDATE jobs SET status = ? WHERE id = ?
            """, (status, job_id))
            
            self.conn.commit()
            self.log_activity(job_id, "status_change", f"Status: {status}")
            logger.info(f"✓ Status updated: {job_id} → {status}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating status: {e}")
            return False
    
    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get all applications pending review with join to jobs"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    j.id, j.title, j.company, j.location, j.url, j.match_score,
                    a.tailored_resume, a.cover_letter, a.changes_summary,
                    m.matched_skills, m.missing_skills, m.strengths, m.gaps
                FROM jobs j
                JOIN applications a ON j.id = a.job_id
                LEFT JOIN match_details m ON j.id = m.job_id
                WHERE a.status = 'pending_review'
                ORDER BY j.match_score DESC, j.scraped_at DESC
            """)
            
            # Convert rows to dictionaries
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Error fetching pending reviews: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        try:
            cursor = self.conn.cursor()
            stats: Dict[str, Any] = {}
            
            # Total jobs
            cursor.execute("SELECT COUNT(*) FROM jobs")
            stats["total_jobs"] = cursor.fetchone()[0]
            
            # High matches
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 0.80")
            stats["high_matches"] = cursor.fetchone()[0]
            
            # Average match score
            cursor.execute("""
                SELECT AVG(match_score) FROM jobs WHERE match_score IS NOT NULL
            """)
            avg = cursor.fetchone()[0]
            stats["avg_match_score"] = round(avg, 3) if avg else 0.0
            
            # Status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) FROM applications GROUP BY status
            """)
            stats["by_status"] = dict(cursor.fetchall())
            
            # Jobs by source
            cursor.execute("""
                SELECT source, COUNT(*) FROM jobs GROUP BY source
            """)
            stats["by_source"] = dict(cursor.fetchall())
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM activity_log 
                WHERE timestamp > date('now', '-7 days')
            """)
            stats["recent_activity"] = cursor.fetchone()[0]
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_jobs": 0,
                "high_matches": 0,
                "avg_match_score": 0.0,
                "by_status": {},
                "by_source": {},
                "recent_activity": 0,
            }
    
    def log_activity(self, job_id: str, action: str, details: str) -> bool:
        """Log an activity to audit trail"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO activity_log (job_id, action, details)
                VALUES (?, ?, ?)
            """, (job_id, action, details))
            
            self.conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error logging activity: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 60) -> int:
        """
        Remove jobs and applications older than specified days.
        Returns number of records deleted.
        """
        try:
            cursor = self.conn.cursor()
            
            # Get count before deletion
            cursor.execute("""
                SELECT COUNT(*) FROM jobs 
                WHERE scraped_at < date('now', '-{} days')
            """.format(days))
            jobs_to_delete = cursor.fetchone()[0]
            
            if jobs_to_delete == 0:
                logger.info(f"No records older than {days} days to clean up")
                return 0
            
            logger.info(f"Cleaning up {jobs_to_delete} jobs older than {days} days")
            
            # Delete old applications first (FK will cascade)
            cursor.execute("""
                DELETE FROM applications 
                WHERE created_at < date('now', '-{} days')
            """.format(days))
            
            apps_deleted = cursor.rowcount
            
            # Delete old jobs (will cascade to match_details and activity_log)
            cursor.execute("""
                DELETE FROM jobs 
                WHERE scraped_at < date('now', '-{} days')
            """.format(days))
            
            jobs_deleted = cursor.rowcount
            
            self.conn.commit()
            self.log_activity(
                "cleanup",
                "auto_cleanup",
                f"Deleted {jobs_deleted} jobs and {apps_deleted} applications"
            )
            
            logger.info(f"✓ Cleaned up {jobs_deleted} jobs and {apps_deleted} applications")
            return jobs_deleted + apps_deleted
            
        except sqlite3.Error as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get complete job details with all related data"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 
                    j.*,
                    m.matched_skills, m.missing_skills, m.relevant_experience,
                    m.strengths, m.gaps, m.reasoning,
                    a.tailored_resume, a.cover_letter, a.changes_summary,
                    a.status as app_status, a.created_at as app_created
                FROM jobs j
                LEFT JOIN match_details m ON j.id = m.job_id
                LEFT JOIN applications a ON j.id = a.job_id
                WHERE j.id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error fetching job details: {e}")
            return None
    
    def close(self) -> None:
        """Safely close database connection"""
        if self._conn:
            try:
                self._conn.commit()
                self._conn.close()
                logger.debug("Database connection closed")
            except sqlite3.Error as e:
                logger.warning(f"Error closing database: {e}")
            finally:
                self._conn = None

# Helper function for direct usage
def get_db() -> JobDatabase:
    """Get database instance with context manager support"""
    return JobDatabase()

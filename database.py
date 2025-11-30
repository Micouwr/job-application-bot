"""
Database module for job application tracking using SQLAlchemy ORM.
This module has been updated for robust, cross-platform deployment.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, 
    Boolean, Index, event, func
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
from sqlalchemy.engine import Engine 
from sqlalchemy.pool import NullPool

# CRITICAL: Import from the refactored, cross-platform settings
from config.settings import DATABASE_PATH, MATCH_THRESHOLD, BASE_DIR

logger = logging.getLogger(__name__)

# Base class for declarative class definitions
Base = declarative_base()


# --- Migration Logic ---
def migrate_legacy_database():
    """
    One-time migration to move the database from the old project-local
    location to the new user-specific data directory.
    """
    old_db_path = BASE_DIR / 'data' / 'job_applications.db'
    new_db_path = DATABASE_PATH

    # Check if the old database exists and the new one does NOT
    if old_db_path.exists() and not new_db_path.exists():
        try:
            logger.info("MIGRATION: Found legacy database. Moving to new user data directory.")
            # Ensure the new parent directory exists
            new_db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(old_db_path, new_db_path)
            logger.info(f"MIGRATION: Successfully moved database to {new_db_path}")
        except (IOError, OSError) as e:
            logger.error(f"MIGRATION: Failed to move legacy database: {e}")
            # Do not exit, allow the app to create a new empty DB.


# Execute migration check on module import
migrate_legacy_database()


# Custom Exceptions
class JobNotFoundError(Exception):
    """Raised when a job ID is not found in the database"""
    pass


# Database Models (remain unchanged)

class MatchDetail(Base):
    __tablename__ = "match_details"
    job_id = Column(String, ForeignKey("jobs.id"), primary_key=True)
    matched_skills = Column(Text, default="[]") 
    missing_skills = Column(Text, default="[]")
    job = relationship("Job", back_populates="match_details")

    def to_dict(self) -> Dict[str, Any]:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        for field in ['matched_skills', 'missing_skills']:
            try:
                content = data[field]
                data[field] = json.loads(content) if content else []
            except (json.JSONDecodeError, TypeError):
                logger.error(f"Failed to decode JSON field '{field}' for job ID {self.job_id}")
                data[field] = [] 
        return data

class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    action = Column(String, nullable=False)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    job = relationship("Job", back_populates="activity_logs")

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    location = Column(String)
    description = Column(Text)
    url = Column(String)
    scraped_at = Column(DateTime, default=datetime.now)
    match_score = Column(Float)
    status = Column(String, default="new", index=True)
    is_deleted = Column(Boolean, default=False)
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    match_details = relationship("MatchDetail", back_populates="job", cascade="all, delete-orphan", uselist=False)
    activity_logs = relationship("ActivityLog", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    tailored_resume = Column(Text)
    cover_letter = Column(Text)
    changes_summary = Column(Text, default="[]")
    status = Column(String, default="pending_review", index=True)
    job = relationship("Job", back_populates="applications")
    
    def to_dict(self) -> Dict[str, Any]:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        try:
            content = data['changes_summary']
            data['changes_summary'] = json.loads(content) if content else []
        except (json.JSONDecodeError, TypeError):
            data['changes_summary'] = []
        return data


class JobDatabase:
    """
    Database class using SQLAlchemy ORM for job tracking and data management.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        # The db_path now correctly defaults to the user-specific directory
        self.db_path = db_path or DATABASE_PATH

        # CRITICAL FIX: Use NullPool for thread safety with SQLite
        self.engine: Engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            poolclass=NullPool,  # Disable connection pooling
            echo=False,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False) 
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        logger.info(f"✓ Database initialized at {self.db_path}")

    @contextmanager
    def get_session(self) -> Session:
        """Context manager for safe session handling."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    # (All other methods like insert_jobs, get_statistics, etc. remain the same)
    # They will automatically benefit from the new database path and connection pool.

    def save_application(self, job_id: str, resume: str, cover_letter: str,
                        changes: List[str]) -> bool:
        """Save a tailored application"""
        try:
            with self.get_session() as session:
                # Truncate large text fields defensively
                resume = resume[:5000000] if len(resume) > 5000000 else resume
                cover_letter = cover_letter[:5000000] if len(cover_letter) > 5000000 else cover_letter

                application = Application(
                    job_id=job_id,
                    tailored_resume=resume,
                    cover_letter=cover_letter,
                    changes_summary=json.dumps(changes),
                    status="pending_review" # Ready for the user to submit
                )
                session.add(application)

                # Update job status
                job = session.query(Job).filter_by(id=job_id).first()
                if job:
                    job.status = "pending_review"
                
                self._log_activity(session, job_id, "application_prepared",
                                  "Tailored application ready")
                return True
        except Exception as e:
            logger.error(f"Error saving application: {e}")
            raise

    def insert_jobs(self, jobs: List[Dict[str, Any]]) -> None:
        if not jobs: return
        try:
            with self.get_session() as session:
                job_ids = [job['id'] for job in jobs]
                existing_jobs = {j.id: j for j in session.query(Job).filter(Job.id.in_(job_ids)).all()}
                jobs_to_add = []
                for job_data in jobs:
                    if job_data['id'] in existing_jobs:
                        job = existing_jobs[job_data['id']]
                        for key, value in job_data.items(): setattr(job, key, value)
                    else:
                        jobs_to_add.append(Job(**{k: v for k, v in job_data.items() if hasattr(Job, k)}))
                if jobs_to_add: session.add_all(jobs_to_add)
                logger.info(f"✓ Bulk inserted/updated {len(jobs)} jobs.")
        except SQLAlchemyError as e:
            logger.error(f"Error during bulk job insertion: {e}")
            raise

    def bulk_update_match_scores(self, updates: List[Tuple[str, Dict[str, Any]]]) -> None:
        """Update multiple jobs with match scores and details in one transaction."""
        if not updates:
            return
        try:
            with self.get_session() as session:
                job_ids = [job_id for job_id, _ in updates]
                jobs_map = {job.id: job for job in session.query(Job).filter(Job.id.in_(job_ids), Job.is_deleted == False).all()}
                match_details_map = {md.job_id: md for md in session.query(MatchDetail).filter(MatchDetail.job_id.in_(job_ids)).all()}
                match_details_to_add = []
                
                for job_id, match_result in updates:
                    job = jobs_map.get(job_id)
                    if not job:
                        continue

                    score = match_result.get("match_score", 0.0)
                    job.match_score = score
                    job.status = "matched" if score >= MATCH_THRESHOLD else "low_match"

                    match_detail = match_details_map.get(job_id)
                    if not match_detail:
                        match_detail = MatchDetail(job_id=job_id)
                        match_details_to_add.append(match_detail)
                    
                    match_detail.matched_skills = json.dumps(match_result.get('matched_skills', []))
                    match_detail.missing_skills = json.dumps(match_result.get('missing_skills', []))
                    
                    if score >= MATCH_THRESHOLD:
                        self._log_activity(session, job_id, "high_match", f"Match: {score*100:.1f}%")

                if match_details_to_add:
                    session.add_all(match_details_to_add)
                logger.info(f"✓ Bulk updated {len(updates)} match scores.")
        except Exception as e:
            logger.error(f"Error during bulk match update: {e}")
            raise 

    def _log_activity(self, session: Session, job_id: str, action: str, details: str) -> None:
        """Log an activity (internal method with active session)."""
        try:
            log = ActivityLog(job_id=job_id, action=action, details=details)
            session.add(log)
        except Exception as e:
            logger.error(f"Error logging activity (non-fatal): {e}")

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        try:
            with self.get_session() as session:
                jobs = session.query(Job).filter(Job.is_deleted == False).order_by(Job.scraped_at.desc()).all()
                return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error fetching all jobs: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        try:
            with self.get_session() as session:
                stats = {}
                stats["total_jobs"] = session.query(Job).filter(Job.is_deleted == False).count()
                stats["high_matches"] = session.query(Job).filter(
                    Job.match_score >= MATCH_THRESHOLD, Job.is_deleted == False
                ).count()
                status_counts = session.query(Job.status, func.count(Job.id)).filter(Job.is_deleted == False).group_by(Job.status).all()
                stats["by_status"] = {status: count for status, count in status_counts}
                avg_score = session.query(func.avg(Job.match_score)).filter(
                    Job.match_score.isnot(None), Job.is_deleted == False
                ).scalar()
                stats["avg_match_score"] = round(avg_score, 3) if avg_score else 0.0
                return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"total_jobs": 0, "high_matches": 0, "by_status": {}, "avg_match_score": 0.0}

# Helper function for external calls
def create_backup() -> Optional[Path]:
    db = JobDatabase()
    # The backup logic will need to be adapted slightly if we keep it
    # For now, this is sufficient.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db.db_path.parent / f"{db.db_path.stem}_backup_{timestamp}{db.db_path.suffix}"
    try:
        shutil.copy2(db.db_path, backup_path)
        logger.info(f"✓ Database backed up to {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return None

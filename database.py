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
    # (other columns and relationships as before)
    
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

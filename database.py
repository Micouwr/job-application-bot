"""
Database module for job application tracking using SQLAlchemy ORM.
Uses SQLite with specific configurations for thread-safe multi-process access.
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
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
from sqlalchemy.engine import Engine 

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)

# Base class for declarative class definitions
Base = declarative_base()


# Custom Exceptions
class JobNotFoundError(Exception):
    """Raised when a job ID is not found in the database"""
    pass


# Database Models
class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    location = Column(String)
    description = Column(Text)
    requirements = Column(Text)
    url = Column(String)
    salary = Column(String)
    job_type = Column(String)  # remote/hybrid/onsite
    experience_level = Column(String)
    source = Column(String)
    scraped_at = Column(DateTime, default=datetime.now)
    match_score = Column(Float)
    status = Column(String, default="new", index=True)
    raw_data = Column(Text)
    is_deleted = Column(Boolean, default=False)  # Soft delete flag
    
    # Relationships: Use delete-orphan for proper cleanup when job is deleted
    match_details = relationship("MatchDetail", back_populates="job", 
                                 cascade="all, delete-orphan", uselist=False) # Use uselist=False as it's a one-to-one
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="job", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_jobs_company_title', 'company', 'title'),
        Index('idx_jobs_match_score', 'match_score'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Job object to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class MatchDetail(Base):
    __tablename__ = "match_details"
    
    job_id = Column(String, ForeignKey("jobs.id"), primary_key=True)
    # Stored as JSON encoded strings
    matched_skills = Column(Text, default="[]") 
    missing_skills = Column(Text, default="[]")
    relevant_experience = Column(Text, default="[]")
    strengths = Column(Text, default="[]")
    gaps = Column(Text, default="[]")
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    job = relationship("Job", back_populates="match_details")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the MatchDetail object to a dictionary, decoding JSON fields."""
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        # Decode JSON fields
        for field in ['matched_skills', 'missing_skills', 'relevant_experience', 'strengths', 'gaps']:
            try:
                # Ensure we handle None/empty string gracefully before loading
                content = data[field]
                data[field] = json.loads(content) if content else []
            except (json.JSONDecodeError, TypeError):
                # Critical fix: If parsing fails, log error and return an empty list
                logger.error(f"Failed to decode JSON field '{field}' for job ID {self.job_id}")
                data[field] = [] 
        return data


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    tailored_resume = Column(Text)
    cover_letter = Column(Text)
    changes_summary = Column(Text, default="[]")  # JSON encoded
    created_at = Column(DateTime, default=datetime.now)
    applied_at = Column(DateTime)
    status = Column(String, default="pending_review", index=True)
    notes = Column(Text)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Application object to a dictionary, decoding JSON fields."""
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        try:
            content = data['changes_summary']
            data['changes_summary'] = json.loads(content) if content else []
        except (json.JSONDecodeError, TypeError):
             logger.error(f"Failed to decode changes_summary for application ID {self.id}")
             data['changes_summary'] = []
        return data


class ActivityLog(Base):
    __tablename__ = "activity_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    action = Column(String, nullable=False)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # Relationships
    job = relationship("Job", back_populates="activity_logs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the ActivityLog object to a dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class JobDatabase:
    """
    Database class using SQLAlchemy ORM for job tracking and data management.
    Handles connection, session, transactions, and core CRUD operations.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self.engine: Engine = create_engine(
            f"sqlite:///{self.db_path}",
            # Allows multiple threads to share the SQLite connection safely
            connect_args={"check_same_thread": False},
            echo=False, # Set to True for verbose SQL logging
            pool_pre_ping=True, 
        )
        Base.metadata.create_all(self.engine)
        # expire_on_commit=False prevents objects from going into the detached state
        # immediately after a commit, which is safer in complex multi-function call chains.
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False) 
        
        # Ensure PRAGMA foreign_keys=ON is run for every new connection
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        logger.info(f"✓ Database initialized at {self.db_path}")

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for safe session handling (transactional unit of work).
        It handles creation, commit, rollback, and closing of the session.
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise # Re-raise exception for caller to handle
        finally:
            session.close()

    def connect(self) -> None:
        """No-op: Connection management is handled by SQLAlchemy pooling."""
        pass
        
    def close(self) -> None:
        """No-op: Connection management is handled by SQLAlchemy pooling."""
        pass

    def insert_jobs(self, jobs: List[Dict[str, Any]]) -> None:
        """Insert or update a list of job listings in a single transaction."""
        if not jobs:
            return

        try:
            with self.get_session() as session:
                job_ids = [job['id'] for job in jobs]
                
                # Fetch existing jobs to determine which to update vs insert
                existing_jobs = {
                    job.id: job for job in session.query(Job).filter(Job.id.in_(job_ids)).all()
                }

                jobs_to_add = []
                for job_data in jobs:
                    job_id = job_data['id']
                    
                    # Size validation for raw_data before processing
                    if 'raw_data' in job_data and job_data['raw_data'] and len(job_data['raw_data']) > 1_000_000:
                        logger.warning(f"Raw data too large for job {job_id}, truncating")
                        job_data['raw_data'] = job_data['raw_data'][:1_000_000]

                    if job_id in existing_jobs:
                        # Update existing record
                        existing = existing_jobs[job_id]
                        # Restore soft-deleted job if it reappears
                        if existing.is_deleted:
                            logger.info(f"Job {job_id} was soft-deleted, restoring")
                            existing.is_deleted = False
                        
                        logger.debug(f"Updating existing job {job_id}")
                        for key, value in job_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # Create new job, filtering out keys not in the model
                        jobs_to_add.append(Job(**{k: v for k, v in job_data.items() if hasattr(Job, k)}))
                        
                        # Log activity for new jobs
                        self._log_activity(session, job_id, "job_added", f"Added: {job_data.get('title', 'N/A')}")

                if jobs_to_add:
                    session.add_all(jobs_to_add)
                
                logger.info(f"✓ Bulk inserted/updated {len(jobs)} jobs.")

        except Exception as e:
            logger.error(f"Error during bulk job insertion: {e}")
            raise 

    def insert_job(self, job: Dict[str, Any]) -> None:
        """Insert a single job (delegates to bulk insertion)."""
        self.insert_jobs([job])

    def bulk_update_match_scores(self, updates: List[Tuple[str, Dict[str, Any]]]) -> None:
        """Update multiple jobs with match scores and details in one transaction."""
        if not updates:
            return

        try:
            with self.get_session() as session:
                job_ids = [job_id for job_id, _ in updates]
                
                # Fetch Jobs and MatchDetails in two separate queries for efficiency
                jobs_map = {
                    job.id: job for job in session.query(Job).filter(
                        Job.id.in_(job_ids), Job.is_deleted == False
                    ).all()
                }
                
                match_details_map = {
                    md.job_id: md for md in session.query(MatchDetail).filter(
                        MatchDetail.job_id.in_(job_ids)
                    ).all()
                }
                
                match_details_to_add = []
                
                for job_id, match_result in updates:
                    job = jobs_map.get(job_id)
                    if not job:
                        logger.warning(f"Job {job_id} not found for match update, skipping.")
                        continue

                    # Update Job table fields
                    score = match_result.get("match_score", 0.0)
                    job.match_score = score
                    # Threshold set to 0.80 for "pending_review" (high match)
                    job.status = "matched" if score >= 0.80 else "low_match" 

                    # Handle MatchDetail table fields
                    match_detail = match_details_map.get(job_id)
                    if not match_detail:
                        match_detail = MatchDetail(job_id=job_id)
                        match_details_to_add.append(match_detail)
                    
                    # Store JSON fields
                    json_fields = ['matched_skills', 'missing_skills', 'relevant_experience', 'strengths', 'gaps']
                    
                    for field in json_fields:
                        data = match_result.get(field, [])
                        
                        # Use list of strings/objects, convert to JSON string
                        json_str = json.dumps(data)
                        
                        # Simple truncation check for excessively long JSON data
                        if len(json_str) > 500_000:
                            logger.warning(f"Match details JSON too large for job {job_id}, truncating list for field {field}.")
                            # Attempt to truncate the list if it's too large before re-serialization
                            if isinstance(data, list) and len(data) > 10:
                                json_str = json.dumps(data[:10])
                        
                        setattr(match_detail, field, json_str)
                            
                    match_detail.reasoning = match_result.get("reasoning", "")
                    match_detail.created_at = datetime.now() # Update timestamp

                    # Log high matches
                    if score >= 0.80:
                        self._log_activity(session, job_id, "high_match", 
                                         f"Match: {score*100:.1f}%")

                if match_details_to_add:
                    session.add_all(match_details_to_add)

                logger.info(f"✓ Bulk updated {len(updates)} match scores.")

        except Exception as e:
            logger.error(f"Error during bulk match update: {e}")
            raise 

    def update_match_score(self, job_id: str, match_result: Dict[str, Any]) -> None:
        """Update job with match score and details (delegates to bulk)"""
        self.bulk_update_match_scores([(job_id, match_result)])

    def save_application(self, job_id: str, tailoring_result: 'TailoringResult') -> bool:
        """
        Save a tailored application from TailoringResult object.
        Extracts resume, cover letter, and metadata from the result.
        """
        try:
            with self.get_session() as session:
                if not tailoring_result.success:
                    logger.error(f"Cannot save failed tailoring for job {job_id}: {tailoring_result.error}")
                    return False

                # Extract content from combined tailored_content
                if tailoring_result.tailored_content:
                    parts = tailoring_result.tailored_content.split("---")
                    resume_text = parts[0].replace("# TAILORED RESUME", "").strip() if len(parts) > 0 else ""
                    cover_letter_text = parts[1].replace("# COVER LETTER", "").strip() if len(parts) > 1 else ""
                else:
                    resume_text = ""
                    cover_letter_text = ""

                # Truncate large fields
                resume_text = resume_text[:5_000_000] if len(resume_text) > 5_000_000 else resume_text
                cover_letter_text = cover_letter_text[:5_000_000] if len(cover_letter_text) > 5_000_000 else cover_letter_text

                # Create changes summary from metadata
                changes_summary = f"AI tailoring complete: {tailoring_result.tokens_used} tokens used"
                
                application = Application(
                    job_id=job_id,
                    tailored_resume=resume_text,
                    cover_letter=cover_letter_text,
                    changes_summary=json.dumps([changes_summary]),
                    status="pending_review"
                )
                session.add(application)
                
                # Update job status
                job = session.query(Job).filter_by(id=job_id).first()
                if job:
                    job.status = "pending_review"
                
                self._log_activity(session, job_id, "application_prepared", 
                                 f"Tailored application ready ({tailoring_result.tokens_used} tokens)")
                return True
        except Exception as e:
            logger.error(f"Error saving application: {e}")
            raise 

    def update_status(self, job_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update job and application status (e.g., to 'applied', 'rejected', etc.)"""
        try:
            with self.get_session() as session:
                # Find the most recent application linked to the job
                application = session.query(Application).filter(
                    Application.job_id == job_id
                ).order_by(Application.created_at.desc()).first()
                
                if not application:
                    # If an application doesn't exist, we update the job status directly
                    job = session.query(Job).filter_by(id=job_id).first()
                    if not job:
                        raise JobNotFoundError(f"Job {job_id} not found")
                else:
                    # Update application status
                    application.status = status
                    if status == "applied":
                        application.applied_at = datetime.now()
                    if notes:
                        # Append new notes to existing ones
                        application.notes = f"{application.notes or ''}\n{notes}".strip()
                    # Also update the job's main status
                    job = application.job # Get job via relationship

                if job:
                    job.status = status
                
                self._log_activity(session, job_id, "status_change", f"Status: {status}")
                return True
        except JobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            raise

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get all jobs that have a prepared application pending user review."""
        try:
            with self.get_session() as session:
                # Query for jobs where the LATEST application status is 'pending_review'
                # Note: We join on Job.id == Application.job_id to ensure a one-to-one mapping in the results
                # We order by match score to prioritize the best candidates.
                query = session.query(Job, Application, MatchDetail).join(
                    Application, Job.id == Application.job_id
                ).outerjoin(
                    MatchDetail, Job.id == MatchDetail.job_id
                ).filter(
                    Application.status == "pending_review", 
                    Job.is_deleted == False
                ).order_by(Job.match_score.desc())
                
                results = []
                for job, application, match_detail in query.all():
                    data = job.to_dict()
                    data.update(application.to_dict())
                    if match_detail:
                        data.update(match_detail.to_dict())
                    results.append(data)
                
                return results
        except Exception as e:
            logger.error(f"Error fetching pending reviews: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about job status and matches."""
        try:
            with self.get_session() as session:
                stats = {}
                
                stats["total_jobs"] = session.query(Job).filter(Job.is_deleted == False).count()
                stats["high_matches"] = session.query(Job).filter(
                    Job.match_score >= 0.80, Job.is_deleted == False
                ).count()
                
                # Status breakdown from the Job table (most comprehensive status)
                status_counts = session.query(Job.status, 
                                            func.count(Job.id)).filter(Job.is_deleted == False).group_by(
                                            Job.status).all()
                stats["by_status"] = {status: count for status, count in status_counts}
                
                # Average match score
                avg_score = session.query(func.avg(Job.match_score)).filter(
                    Job.match_score.isnot(None), Job.is_deleted == False
                ).scalar()
                stats["avg_match_score"] = round(avg_score, 3) if avg_score else 0.0
                
                # Recent activity
                recent_activity = session.query(ActivityLog).order_by(
                    ActivityLog.timestamp.desc()).limit(10).all()
                stats["recent_activity"] = [log.to_dict() for log in recent_activity]
                
                return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"total_jobs": 0, "high_matches": 0, "by_status": {}, "avg_match_score": 0.0, "recent_activity": []}

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all non-deleted jobs for display or export."""
        try:
            with self.get_session() as session:
                jobs = session.query(Job).filter(Job.is_deleted == False).order_by(Job.scraped_at.desc()).all()
                return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error fetching all jobs: {e}")
            return []

    def search_jobs(self, query: str) -> List[Dict[str, Any]]:
        """Full-text search across job titles, descriptions, and companies."""
        # Note: For true FTS, you would use a dedicated SQLite extension or move to Postgres/MySQL.
        # This uses simple LIKE search which is fine for small databases.
        try:
            # Add wildcard characters to the query for better partial matches
            search_pattern = f"%{query.lower()}%" 
            
            with self.get_session() as session:
                jobs = session.query(Job).filter(
                    (func.lower(Job.title).like(search_pattern)) |
                    (func.lower(Job.description).like(search_pattern)) |
                    (func.lower(Job.company).like(search_pattern)),
                    Job.is_deleted == False
                ).order_by(Job.match_score.desc()).all()
                return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return []

    def _log_activity(self, session: Session, job_id: str, action: str, details: str) -> None:
        """Log an activity (internal method with active session)."""
        try:
            log = ActivityLog(job_id=job_id, action=action, details=details)
            session.add(log)
        except Exception as e:
            # We don't want a logging failure to crash the main transaction
            logger.error(f"Error logging activity (non-fatal): {e}")

    def create_backup(self) -> Optional[Path]:
        """Create a physical backup of the SQLite database file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.parent / f"{self.db_path.stem}_backup_{timestamp}{self.db_path.suffix}"
        
        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            # Use shutil.copy2 to preserve metadata (like timestamps)
            shutil.copy2(self.db_path, backup_path) 
            logger.info(f"✓ Database backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def soft_delete_job(self, job_id: str) -> bool:
        """Soft delete a job (hides from most queries but retains history)."""
        try:
            with self.get_session() as session:
                job = session.query(Job).filter_by(id=job_id).first()
                if not job:
                    raise JobNotFoundError(f"Job {job_id} not found")
                
                job.is_deleted = True
                job.status = "archived"
                
                self._log_activity(session, job_id, "soft_delete", "Job archived")
                return True
        except JobNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error soft deleting job: {e}")
            raise


# Helper function at module level
def create_backup() -> Optional[Path]:
    """Create a backup of the database (now creates a temporary instance to run)"""
    db = JobDatabase()
    return db.create_backup()


if __name__ == "__main__":
    # Test database functionality
    db = JobDatabase()
    
    # Example: Create a backup
    backup = db.create_backup()
    if backup:
        print(f"✓ Created backup: {backup}")
    
    # Print statistics
    stats = db.get_statistics()
    print("\n=== Database Statistics ===")
    print(f"Total non-deleted jobs: {stats['total_jobs']}")
    print(f"High matches (>= 80%): {stats['high_matches']}")
    print(f"Average match score: {stats['avg_match_score']*100:.1f}%")
    print("Status Breakdown:")
    for status, count in stats['by_status'].items():
        print(f"  - {status}: {count}")
    print("Recent Activity:")
    for log in stats['recent_activity']:
         print(f"  [{log['timestamp'].strftime('%Y-%m-%d %H:%M')}] {log.get('job_id', 'N/A')}: {log['action']} - {log['details']}")
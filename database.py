"""
Database module for job application tracking using SQLAlchemy ORM.
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
# CRITICAL FIX: Removed StaticPool, allowing default QueuePool for better thread safety
from sqlalchemy.engine import Engine 

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)

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
    
    # Relationships
    match_details = relationship("MatchDetail", back_populates="job", cascade="all, delete-orphan") # Use delete-orphan for proper cleanup
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="job", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_jobs_company_title', 'company', 'title'),
        Index('idx_jobs_match_score', 'match_score'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class MatchDetail(Base):
    __tablename__ = "match_details"
    
    job_id = Column(String, ForeignKey("jobs.id"), primary_key=True)
    matched_skills = Column(Text)  # JSON encoded
    missing_skills = Column(Text)  # JSON encoded
    relevant_experience = Column(Text)  # JSON encoded
    strengths = Column(Text)  # JSON encoded
    gaps = Column(Text)  # JSON encoded
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    job = relationship("Job", back_populates="match_details")
    
    def to_dict(self) -> Dict[str, Any]:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        # Decode JSON fields
        for field in ['matched_skills', 'missing_skills', 'relevant_experience', 'strengths', 'gaps']:
            try:
                if data[field]:
                    data[field] = json.loads(data[field])
            except (json.JSONDecodeError, TypeError):
                data[field] = [] # Set to empty list on error
        return data


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    tailored_resume = Column(Text)
    cover_letter = Column(Text)
    changes_summary = Column(Text)  # JSON encoded
    created_at = Column(DateTime, default=datetime.now)
    applied_at = Column(DateTime)
    status = Column(String, default="pending_review", index=True)
    notes = Column(Text)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    
    def to_dict(self) -> Dict[str, Any]:
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        try:
            if data['changes_summary']:
                data['changes_summary'] = json.loads(data['changes_summary'])
        except (json.JSONDecodeError, TypeError):
             data['changes_summary'] = [] # Set to empty list on error
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
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class JobDatabase:
    """
    Enhanced database class with SQLAlchemy ORM, connection pooling, and backups.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self.engine: Engine = create_engine(
            f"sqlite:///{self.db_path}",
            # CRITICAL FIX: Removed StaticPool for thread safety in multi-threaded environment
            # Default QueuePool is used, safer for SQLite in threads.
            connect_args={"check_same_thread": False},
            echo=False,
            pool_pre_ping=True,  # Verify connections before using
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False) # expire_on_commit=False for thread context
        
        # Enable foreign keys
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        logger.info(f"✓ Database initialized at {self.db_path}")

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for safe session handling.
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # CRITICAL FIX: Added bulk insertion method for performance
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
                        if existing.is_deleted:
                            logger.info(f"Job {job_id} was soft-deleted, restoring")
                            existing.is_deleted = False
                        
                        logger.debug(f"Updating existing job {job_id}")
                        for key, value in job_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # Create new job
                        jobs_to_add.append(Job(**{k: v for k, v in job_data.items() if hasattr(Job, k)}))
                        
                        # Log activity for new jobs
                        self._log_activity(session, job_id, "job_added", f"Added: {job_data['title']}")

                if jobs_to_add:
                    session.add_all(jobs_to_add)
                
                logger.info(f"✓ Bulk inserted/updated {len(jobs)} jobs.")

        except Exception as e:
            logger.error(f"Error during bulk job insertion: {e}")
            raise # Let exception propagate for caller (main.py) to handle

    def insert_job(self, job: Dict[str, Any]) -> None:
        """
        Single job insert method now delegates to the bulk method (Kept for compatibility,
        but recommended to use bulk_insert for batches).
        """
        self.insert_jobs([job])

    # CRITICAL FIX: Added bulk update method for match scores
    def bulk_update_match_scores(self, updates: List[Tuple[str, Dict[str, Any]]]) -> None:
        """Update multiple jobs with match scores and details in one transaction."""
        if not updates:
            return

        try:
            with self.get_session() as session:
                job_ids = [job_id for job_id, _ in updates]
                jobs = session.query(Job).filter(Job.id.in_(job_ids), Job.is_deleted == False).all()
                jobs_map = {job.id: job for job in jobs}
                
                match_details = session.query(MatchDetail).filter(MatchDetail.job_id.in_(job_ids)).all()
                match_details_map = {md.job_id: md for md in match_details}
                
                match_details_to_add = []
                
                for job_id, match_result in updates:
                    job = jobs_map.get(job_id)
                    if not job:
                        logger.warning(f"Job {job_id} not found for match update, skipping.")
                        continue

                    # Update Job table fields
                    score = match_result["match_score"]
                    job.match_score = score
                    job.status = "matched" if score >= 0.80 else "low_match"

                    # Handle MatchDetail table fields
                    match_detail = match_details_map.get(job_id)
                    if not match_detail:
                        match_detail = MatchDetail(job_id=job_id)
                        match_details_to_add.append(match_detail)
                    
                    # Validate JSON size before storing
                    json_fields = ['matched_skills', 'missing_skills', 'relevant_experience', 'strengths', 'gaps']
                    total_json_size = 0
                    
                    for field in json_fields:
                        data = match_result.get(field, [])
                        if data:
                            json_str = json.dumps(data)
                            total_json_size += len(json_str)
                            # Simple truncation check
                            if total_json_size > 500_000 and len(data) > 10:
                                logger.warning(f"Match details too large for job {job_id}, truncating field {field}.")
                                data = data[:10]
                            setattr(match_detail, field, json.dumps(data))
                        else:
                            setattr(match_detail, field, json.dumps([]))
                            
                    match_detail.reasoning = match_result.get("reasoning", "")

                    # Log high matches
                    if score >= 0.80:
                        self._log_activity(session, job_id, "high_match", 
                                         f"Match: {score*100:.1f}%")

                if match_details_to_add:
                    session.add_all(match_details_to_add)

                logger.info(f"✓ Bulk updated {len(updates)} match scores.")

        except Exception as e:
            logger.error(f"Error during bulk match update: {e}")
            raise # Let exception propagate for caller (main.py) to handle

    # Single update_match_score method for compatibility
    def update_match_score(self, job_id: str, match_result: Dict[str, Any]) -> None:
        """Update job with match score and details (delegates to bulk)"""
        self.bulk_update_match_scores([(job_id, match_result)])

    def save_application(self, job_id: str, resume: str, cover_letter: str, 
                        changes: List[str]) -> bool:
        """Save a tailored application"""
        try:
            with self.get_session() as session:
                # Validate text field sizes
                if len(resume) > 5_000_000:
                    logger.warning(f"Resume too large for job {job_id}, truncating")
                    resume = resume[:5_000_000]
                
                if len(cover_letter) > 5_000_000:
                    logger.warning(f"Cover letter too large for job {job_id}, truncating")
                    cover_letter = cover_letter[:5_000_000]
                
                application = Application(
                    job_id=job_id,
                    tailored_resume=resume,
                    cover_letter=cover_letter,
                    changes_summary=json.dumps(changes),
                    status="pending_review"
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
            raise # Let exception propagate

    def update_status(self, job_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update application status"""
        try:
            with self.get_session() as session:
                # Use exception for not found
                application = session.query(Application).join(Job).filter(
                    Application.job_id == job_id, Job.is_deleted == False
                ).first()
                if not application:
                    raise JobNotFoundError(f"Application for job {job_id} not found")
                
                application.status = status
                if status == "applied":
                    application.applied_at = datetime.now()
                if notes:
                    application.notes = f"{application.notes or ''}\n{notes}".strip()
                
                # Update job status
                job = session.query(Job).filter_by(id=job_id).first()
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
        """Get all applications pending review"""
        try:
            with self.get_session() as session:
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
        """Get comprehensive statistics"""
        try:
            # Note: Using Session directly here as this is a read-only transaction
            with self.get_session() as session:
                stats = {}
                
                stats["total_jobs"] = session.query(Job).filter(Job.is_deleted == False).count()
                stats["high_matches"] = session.query(Job).filter(
                    Job.match_score >= 0.80, Job.is_deleted == False
                ).count()
                
                # Status breakdown
                status_counts = session.query(Application.status, 
                                            func.count(Application.id)).group_by(
                                            Application.status).all()
                stats["by_status"] = {status: count for status, count in status_counts}
                
                # Average match score
                avg_score = session.query(func.avg(Job.match_score)).filter(
                    Job.match_score.isnot(None), Job.is_deleted == False
                ).scalar()
                stats["avg_match_score"] = round(avg_score, 3) if avg_score else 0
                
                # Recent activity
                recent_activity = session.query(ActivityLog).order_by(
                    ActivityLog.timestamp.desc()).limit(10).all()
                stats["recent_activity"] = [log.to_dict() for log in recent_activity]
                
                return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"total_jobs": 0, "high_matches": 0, "by_status": {}, "avg_match_score": 0}

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """QoL: Get all jobs for export"""
        try:
            with self.get_session() as session:
                jobs = session.query(Job).filter(Job.is_deleted == False).all()
                return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error fetching all jobs: {e}")
            return []

    def search_jobs(self, query: str) -> List[Dict[str, Any]]:
        """QoL: Full-text search across job descriptions"""
        try:
            with self.get_session() as session:
                jobs = session.query(Job).filter(
                    (Job.title.contains(query)) |
                    (Job.description.contains(query)) |
                    (Job.company.contains(query)),
                    Job.is_deleted == False
                ).all()
                return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return []

    def _log_activity(self, session: Session, job_id: str, action: str, details: str) -> None:
        """Log an activity (internal method with session)"""
        try:
            log = ActivityLog(job_id=job_id, action=action, details=details)
            session.add(log)
        except Exception as e:
            logger.error(f"Error logging activity: {e}")

    def create_backup(self) -> Optional[Path]:
        """
        QoL: Create a backup of the database
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.parent / f"backup_{timestamp}.db"
        
        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✓ Database backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def close(self) -> None:
        """Close the database connection (no-op as context managers handle this)"""
        pass

    def soft_delete_job(self, job_id: str) -> bool:
        """
        QoL: Soft delete a job (keeps history but hides from queries)
        """
        try:
            with self.get_session() as session:
                job = session.query(Job).filter_by(id=job_id).first()
                if not job:
                    raise JobNotFoundError(f"Job {job_id} not found")
                
                job.is_deleted = True
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
    print(f"Total jobs: {stats['total_jobs']}")
    print(f"High matches: {stats['high_matches']}")
    print(f"Average match score: {stats['avg_match_score']*100:.1f}%")

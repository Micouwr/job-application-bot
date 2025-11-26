"""
Database module for job application tracking using SQLAlchemy ORM.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, 
    Boolean, Index, event
)
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
from sqlalchemy.pool import StaticPool

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)

Base = declarative_base()


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
    
    # Relationships
    match_details = relationship("MatchDetail", back_populates="job", cascade="all, delete-orphan")
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
            if data[field]:
                data[field] = json.loads(data[field])
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
        if data['changes_summary']:
            data['changes_summary'] = json.loads(data['changes_summary'])
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
    ✅ QoL: Enhanced database class with SQLAlchemy ORM, connection pooling, and backups.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
        # Enable foreign keys
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        logger.info(f"✓ Database initialized at {self.db_path}")

    @contextmanager
    def get_session(self) -> Session:
        """✅ QoL: Context manager for safe session handling"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def insert_job(self, job: Dict[str, Any]) -> bool:
        """ Insert a new job listing """
        try:
            with self.get_session() as session:
                # Check if job exists
                existing = session.query(Job).filter_by(id=job["id"]).first()
                if existing:
                    logger.info(f"Job {job['id']} already exists, updating")
                    # Update existing record
                    for key, value in job.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # Create new job
                    db_job = Job(**{k: v for k, v in job.items() if hasattr(Job, k)})
                    session.add(db_job)
                
                # Log activity
                self._log_activity(session, job["id"], "job_added", f"Added: {job['title']}")
                return True
        except Exception as e:
            logger.error(f"Error inserting job: {e}")
            return False

    def update_match_score(self, job_id: str, match_result: Dict[str, Any]) -> bool:
        """  Update job with match score and details """
        try:
            with self.get_session() as session:
                # Update job score and status
                job = session.query(Job).filter_by(id=job_id).first()
                if not job:
                    logger.error(f"Job {job_id} not found")
                    return False
                
                job.match_score = match_result["match_score"]
                job.status = "matched" if match_result["match_score"] >= 0.80 else "low_match"

                # Update or create match details
                match_detail = session.query(MatchDetail).filter_by(job_id=job_id).first()
                if not match_detail:
                    match_detail = MatchDetail(job_id=job_id)
                    session.add(match_detail)
                
                # Store JSON fields
                for field in ['matched_skills', 'missing_skills', 'relevant_experience', 'strengths', 'gaps']:
                    setattr(match_detail, field, json.dumps(match_result.get(field, [])))
                match_detail.reasoning = match_result.get("reasoning", "")

                # Log high matches
                if match_result["match_score"] >= 0.80:
                    self._log_activity(session, job_id, "high_match", 
                                     f"Match: {match_result['match_score']*100:.1f}%")
                
                return True
        except Exception as e:
            logger.error(f"Error updating match score: {e}")
            return False

    def save_application(self, job_id: str, resume: str, cover_letter: str, 
                        changes: List[str]) -> bool:
        """  Save a tailored application """
        try:
            with self.get_session() as session:
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
            return False

    def update_status(self, job_id: str, status: str, notes: Optional[str] = None) -> bool:
        """ Update application status """
        try:
            with self.get_session() as session:
                # Update application
                application = session.query(Application).filter_by(job_id=job_id).first()
                if application:
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
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """ Get all applications pending review """
        try:
            with self.get_session() as session:
                query = session.query(Job, Application, MatchDetail).join(
                    Application, Job.id == Application.job_id
                ).outerjoin(
                    MatchDetail, Job.id == MatchDetail.job_id
                ).filter(Application.status == "pending_review").order_by(Job.match_score.desc())
                
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
        """  Get comprehensive statistics """
        try:
            with self.get_session() as session:
                stats = {}
                
                stats["total_jobs"] = session.query(Job).count()
                stats["high_matches"] = session.query(Job).filter(Job.match_score >= 0.80).count()
                
                # Status breakdown
                status_counts = session.query(Application.status, 
                                            func.count(Application.id)).group_by(
                                            Application.status).all()
                stats["by_status"] = {status: count for status, count in status_counts}
                
                # Average match score
                from sqlalchemy.sql import func
                avg_score = session.query(func.avg(Job.match_score)).filter(
                    Job.match_score.isnot(None)).scalar()
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
        """  QoL: Get all jobs for export """
        try:
            with self.get_session() as session:
                jobs = session.query(Job).all()
                return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error fetching all jobs: {e}")
            return []

    def search_jobs(self, query: str) -> List[Dict[str, Any]]:
        """  QoL: Full-text search across job descriptions """
        try:
            with self.get_session() as session:
                jobs = session.query(Job).filter(
                    (Job.title.contains(query)) |
                    (Job.description.contains(query)) |
                    (Job.company.contains(query))
                ).all()
                return [job.to_dict() for job in jobs]
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return []

    def _log_activity(self, session: Session, job_id: str, action: str, details: str) -> None:
        """  Log an activity (internal method with session) """
        try:
            log = ActivityLog(job_id=job_id, action=action, details=details)
            session.add(log)
        except Exception as e:
            logger.error(f"Error logging activity: {e}")

    def create_backup(self, backup_path: Optional[Path] = None) -> Optional[Path]:
        """
        ✅ QoL: Create a backup of the database
        """
        if not backup_path:
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
        """  Close the database connection """
        # SQLAlchemy handles this automatically with context managers


# Helper function at module level
def create_backup() -> Optional[Path]:
    """Create a backup of the database"""
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

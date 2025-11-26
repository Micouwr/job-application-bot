#!/usr/bin/env python3
"""
Job Application Bot - Main Entry Point
Author: Ryan Micou
"""

import logging
import sys
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    COVER_LETTERS_DIR,
    RESUMES_DIR,
    LOG_FILE,
    MATCH_THRESHOLD,
    validate_config,
    Config
)
from database import JobDatabase
from matcher import JobMatcher
from scraper import JobScraper
from tailor import ResumeTailor

# Setup logging with level from config
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

class JobApplicationBot:
    """
    The main orchestrator for the Job Application Bot.
    Uses context manager for proper resource cleanup.
    """
    
    def __init__(self) -> None:
        """Initializes the JobApplicationBot."""
        logger.info("=" * 80)
        logger.info("Job Application Bot Starting")
        logger.info("=" * 80)
        
        # Validate configuration (fails fast if invalid)
        try:
            validate_config()
            logger.info("Configuration validated")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.db = JobDatabase()
        self.scraper = JobScraper(self.db)  # Pass db for duplicate checking
        self.matcher = JobMatcher()
        self.tailor = ResumeTailor()
        
        logger.info("All components initialized")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup"""
        if exc_type:
            logger.error(f"Exiting with error: {exc_val}")
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources and old data"""
        try:
            # Run auto-cleanup (60 days)
            deleted = self.db.cleanup_old_data(days=60)
            logger.info(f"Auto-cleanup removed {deleted} old records")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
        finally:
            self.db.close()
            logger.info("Database connection closed")
    
    def run_pipeline(self, manual_jobs: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Runs the complete job application pipeline.
        Fails fast on any critical error.
        """
        logger.info("\n" + "=" * 80)
        logger.info("STARTING PIPELINE")
        logger.info("=" * 80 + "\n")
        
        try:
            # Step 1: Get jobs
            jobs = self._get_jobs(manual_jobs)
            
            # Step 2: Match jobs
            high_matches = self._match_jobs(jobs)
            
            # Step 3: Tailor applications
            if high_matches:
                self._create_applications(high_matches)
            
            # Step 4: Summary
            self._print_summary()
            
        except KeyboardInterrupt:
            logger.warning("Pipeline interrupted by user")
            sys.exit(1)
        except RuntimeError as e:
            logger.error(f"Pipeline failed: {e}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected pipeline failure: {e}", exc_info=True)
            raise
    
    def _get_jobs(self, manual_jobs: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Get jobs with validation"""
        if manual_jobs:
            # Validate each job has required fields
            validated_jobs = []
            for job in manual_jobs:
                if not all(key in job for key in ["id", "title", "company"]):
                    logger.error(f"Invalid job data: missing required fields in {job}")
                    raise ValueError(f"Invalid job data: {job}")
                validated_jobs.append(job)
            logger.info(f"Using {len(validated_jobs)} manually added jobs")
            return validated_jobs
        
        logger.warning("No jobs provided. Use --interactive mode or add_manual_job().")
        return []
    
    def _match_jobs(self, jobs: List[Dict[str, Any]]) -> List[tuple]:
        """Match jobs and return high matches"""
        logger.info("\nStep 2: Matching jobs against resume...")
        high_matches: List[tuple] = []
        
        for job in jobs:
            match_result = self.matcher.match_job(job)
            self.db.update_match_score(job["id"], match_result)
            
            score = match_result["match_score"]
            logger.info(f"  {job['title']} at {job['company']}: {score*100:.1f}%")
            
            if score >= MATCH_THRESHOLD:
                high_matches.append((job, match_result))
                logger.info(f"  HIGH MATCH - {match_result['recommendation']}")
        
        logger.info(
            f"\nFound {len(high_matches)}/{len(jobs)} high matches (≥{MATCH_THRESHOLD*100}%)"
        )
        return high_matches
    
    def _create_applications(self, high_matches: List[tuple]) -> None:
        """Create tailored applications with error handling"""
        logger.info("\nStep 3: Creating tailored applications...")
        
        for job, match in high_matches:
            logger.info(f"\nTailoring for: {job['title']} at {job['company']}")
            
            try:
                application = self.tailor.tailor_application(job, match)
                
                # Save to database
                self.db.save_application(
                    job["id"],
                    application["resume_text"],
                    application["cover_letter"],
                    application["changes"],
                )
                
                # Save to files
                self._save_application_files(job, application)
                
                logger.info("  Application generated")
                
            except RuntimeError as e:
                # Re-raise RuntimeError from tailor
                logger.error(f"  Error in tailoring: {e}")
                raise
            except Exception as e:
                # Unexpected error - log and re-raise
                logger.critical(f"  Unexpected error tailoring {job['title']}: {e}", exc_info=True)
                raise RuntimeError(f"Failed to tailor {job['title']}: {e}") from e
    
    def add_manual_job(
        self,
        title: str,
        company: str = "Unknown",
        url: str = "",
        description: str = "",
        location: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Adds a job manually with validation.
        Returns job dict or None if duplicate/invalid.
        """
        # Input validation
        if not title or len(title.strip()) == 0:
            logger.error("Job title cannot be empty")
            return None
        
        if len(title) > 200:
            logger.error(f"Job title too long: {len(title)} chars (max 200)")
            return None
        
        if url and not url.startswith(("http://", "https://")):
            logger.warning(f"Invalid URL format: {url}")
            url = ""
        
        job = self.scraper.add_manual_job(title, company, url, description, location)
        
        if job:
            logger.info(f"Added: {title} at {company}")
        return job
    
    def run_interactive(self) -> None:
        """Interactive mode with improved validation"""
        logger.info("\n" + "=" * 80)
        logger.info("INTERACTIVE MODE")
        logger.info("=" * 80 + "\n")
        
        jobs: List[Dict[str, Any]] = []
        
        print("Add jobs manually (type 'done' when finished)\n")
        
        while True:
            print("\n" + "-" * 40)
            title = input("Job Title (or 'done'): ").strip()
            
            if title.lower() == "done":
                break
            
            if not title:
                print("Job title cannot be empty. Please try again.")
                continue
            
            if len(title) > 200:
                print("Job title too long (max 200 chars). Please try again.")
                continue
            
            company = input("Company: ").strip()
            if not company:
                company = "Unknown"
                print("Using default company: Unknown")
            
            location = input(f"Location [{Config.JOB_LOCATION}]: ").strip() or Config.JOB_LOCATION
            
            url = input("Job URL (optional): ").strip()
            if url and not url.startswith(("http://", "https://")):
                print("Invalid URL format, skipping...")
                url = ""
            
            print("\nPaste job description (press Enter twice when done):")
            description_lines = []
            while True:
                line = input()
                if line == "" and description_lines:
                    # Empty line after content means done
                    break
                description_lines.append(line)
            description = "\n".join(description_lines).strip()
            
            if not description:
                print("No description provided. Skipping this job.")
                continue
            
            job = self.add_manual_job(title, company, url, description, location)
            if job:
                jobs.append(job)
                print(f"Added {title} at {company}")
        
        if jobs:
            logger.info(f"\nProcessing {len(jobs)} jobs...")
            self.run_pipeline(manual_jobs=jobs)
        else:
            logger.info("No jobs added.")
    
    def review_pending(self) ->

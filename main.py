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
    
    def review_pending(self) -> None:
        """Shows all applications pending review"""
        pending = self.db.get_pending_reviews()
        
        if not pending:
            print("\nNo applications pending review.")
            return
        
        print("\n" + "=" * 80)
        print(f"PENDING REVIEW ({len(pending)} applications)")
        print("=" * 80 + "\n")
        
        for i, app in enumerate(pending, 1):
            print(f"{i}. {app['title']} at {app['company']}")
            print(f"   Match Score: {app['match_score']*100:.1f}%")
            print(f"   Location: {app['location']}")
            print(f"   URL: {app['url']}")
            
            # Safely parse changes
            changes = self._safe_parse_changes(app.get("changes_summary", "[]"))
            if changes:
                print(f"   Changes: {', '.join(changes[:3])}")  # Show max 3
            print()
    
    def _safe_parse_changes(self, changes_json: str) -> List[str]:
        """Safely parse changes JSON"""
        try:
            import json
            changes = json.loads(changes_json) if changes_json else []
            return [str(c).strip() for c in changes if c]
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid JSON in changes summary")
            return []
    
    def approve_application(self, job_id: str) -> None:
        """Approve an application"""
        self.db.update_status(job_id, "applied")
        logger.info(f"Application approved: {job_id}")
    
    def _save_application_files(self, job: Dict[str, Any], application: Dict[str, Any]) -> None:
        """
        Saves tailored resume and cover letter with safe filenames.
        Prevents overwrites and path traversal.
        """
        def sanitize_filename(name: str, max_length: int = 40) -> str:
            """Sanitize filename to prevent security issues"""
            if not name:
                return "unknown"
            # Remove dangerous characters
            sanitized = re.sub(r'[<>:\"/\\|?*\x00-\x1f]', '', name)
            # Replace path separators
            sanitized = sanitized.replace('..', '')
            # Limit length
            sanitized = sanitized[:max_length].strip()
            return sanitized or "unknown"
        
        safe_company = sanitize_filename(job["company"])
        job_id_short = job["id"][-8:]  # Last 8 chars of job ID for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        base_name = f"{safe_company}_{job_id_short}_{timestamp}"
        
        try:
            # Ensure directories exist with permissions check
            RESUMES_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
            COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
            
            resume_file = RESUMES_DIR / f"{base_name}_resume.txt"
            cover_file = COVER_LETTERS_DIR / f"{base_name}_cover_letter.txt"
            
            # Double-check for existing files (defensive)
            if resume_file.exists():
                logger.warning(f"File exists, adding UUID: {resume_file}")
                unique = str(uuid.uuid4())[:8]
                resume_file = resume_file.with_stem(f"{resume_file.stem}_{unique}")
                cover_file = cover_file.with_stem(f"{cover_file.stem}_{unique}")
            
            # Write files
            resume_file.write_text(application["resume_text"], encoding="utf-8")
            cover_file.write_text(application["cover_letter"], encoding="utf-8")
            
            logger.info(f"Saved to: {resume_file.name} and {cover_file.name}")
            
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Failed to save application files: {e}")
            raise RuntimeError(f"Cannot save files for {job['title']}: {e}")
    
    def _print_summary(self) -> None:
        """Print pipeline execution summary"""
        stats = self.db.get_statistics()
        
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Total Jobs: {stats['total_jobs']}")
        print(f"High Matches (≥80%): {stats['high_matches']}")
        print(f"Applications Prepared: {stats['by_status'].get('pending_review', 0)}")
        print(f"Average Match Score: {stats['avg_match_score']*100:.1f}%")
        print("\nNext Steps:")
        print("1. Review applications: python main.py --review")
        print("2. Check output/ folder for tailored resumes and cover letters")
        print("3. Open database with: sqlite3 data/job_applications.db")
        print("=" * 80 + "\n")

def main() -> None:
    """
    Main entry point with proper error handling and cleanup.
    Uses context manager to ensure resources are released.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Job Application Bot - Automated IT Infrastructure Job Applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --interactive    # Add jobs manually
  python main.py --review         # Review pending applications
  python main.py --stats          # Show statistics
  python main.py --cleanup        # Clean old records
        """
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode (add jobs manually)"
    )
    parser.add_argument(
        "--review", "-r",
        action="store_true",
        help="Review pending applications"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show statistics"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up old records (60 days)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Adjust log level if debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    try:
        with JobApplicationBot() as bot:
            if args.interactive:
                bot.run_interactive()
            elif args.review:
                bot.review_pending()
            elif args.stats:
                stats = bot.db.get_statistics()
                print("\n=== STATISTICS ===")
                print(f"Total Jobs: {stats['total_jobs']}")
                print(f"High Matches: {stats['high_matches']}")
                print(f"Avg Match Score: {stats['avg_match_score']*100:.1f}%")
                print("\nBy Status:")
                for status, count in stats.get("by_status", {}).items():
                    print(f"  {status}: {count}")
            elif args.cleanup:
                deleted = bot.db.cleanup_old_data(days=60)
                print(f"Cleaned up {deleted} old records")
            else:
                # Show usage
                parser.print_help()
                print("\nQuick start: python main.py --interactive")
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

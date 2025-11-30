#!/usr/bin/env python3
"""
Job Application Bot - Main Entry Point
Author: Ryan Micou
"""

import json
import logging
import sys
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
import time # Added for simulating thread pause

# Mandatory Third-Party Imports
from tqdm import tqdm

# Local Imports (Assuming JobDatabase is a lightweight class that manages connections)
from config.settings import (
    COVER_LETTERS_DIR,
    JOB_KEYWORDS,
    JOB_LOCATION,
    LOG_FILE,
    LOG_LEVEL,
    MATCH_THRESHOLD,
    MAX_JOBS_PER_PLATFORM,
    RESUME_DATA,
    RESUMES_DIR,
    config,
)
from database import JobDatabase, create_backup, JobNotFoundError
from matcher import JobMatcher
# Assuming JobScraper handles the base logic and JobBoardIntegration handles API calls
from scraper import JobScraper, JobBoardIntegration 
from tailor import ResumeTailor

# Setup logging with configurable level
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class JobApplicationBot:
    """
    The main orchestrator for the Job Application Bot.
    """

    def __init__(self) -> None:
        """Initializes the JobApplicationBot."""
        logger.info("=" * 80)
        logger.info("Job Application Bot Starting")
        logger.info("=" * 80)

        # CRITICAL FIX 1: Lazy Database Connection/Thread-local Handling
        # The main bot object holds the DB class reference, but connections are managed per task/thread.
        self.db_class = JobDatabase 
        self.scraper = JobScraper()
        self.matcher = JobMatcher(RESUME_DATA) # Pass resume data to matcher on init
        self.tailor = ResumeTailor(RESUME_DATA)

        if config.scraper_api_key:
            # We assume JobBoardIntegration takes the ScraperAPI key for web scraping
            self.job_boards = JobBoardIntegration(config.scraper_api_key)
        else:
            self.job_boards = None
            logger.info("ℹ️ No ScraperAPI key found. Manual job entry or local scraper only.")

        self.executor = ThreadPoolExecutor(max_workers=5)
        
        logger.info("✓ All components initialized")

    def run_pipeline_async(self, manual_jobs: Optional[List[Dict]] = None, dry_run: bool = False, callback: Optional[Callable] = None) -> None:
        """
        Submits the complete job application pipeline to a thread pool executor.
        """
        future = self.executor.submit(self._pipeline_task, manual_jobs, dry_run)
        if callback:
            # Ensure callback handles the result from the thread
            future.add_done_callback(lambda f: callback(f.result()))
        return future

    def _pipeline_task(self, manual_jobs: Optional[List[Dict]], dry_run: bool) -> bool:
        """
        Internal, synchronous task for running the pipeline.
        
        CRITICAL FIX 2: Instantiate JobDatabase connection *inside* the thread for safety.
        """
        db = self.db_class() # New database instance/connection for this thread
        
        try:
            self.run_pipeline(db, manual_jobs=manual_jobs, dry_run=dry_run)
            return True
        except Exception as e:
            logger.exception("FATAL: Pipeline task failed.")
            return False

    # CRITICAL FIX 3: Accept database object as the first argument
    def run_pipeline(self, db: JobDatabase, manual_jobs: Optional[List[Dict]] = None, dry_run: bool = False) -> None:
        """
        Runs the complete job application pipeline (synchronous version).
        
        Args:
            db: The database connection object for this thread/task.
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"STARTING PIPELINE{' (DRY RUN)' if dry_run else ''}")
        logger.info("=" * 80 + "\n")

        # Step 1: Get jobs
        if manual_jobs:
            jobs = manual_jobs
            logger.info(f"Using {len(jobs)} manually added jobs")
        else:
            logger.info("Step 1: Scraping jobs...")
            if self.job_boards:
                # Assuming scrape_all returns a list of job dicts
                jobs = self.job_boards.scrape_all(
                    keywords=JOB_KEYWORDS,
                    location=JOB_LOCATION,
                    max_jobs=MAX_JOBS_PER_PLATFORM
                )
                logger.info(f"Scraped {len(jobs)} jobs from job boards")
            else:
                logger.warning("Automated scraping not configured. Use interactive mode.")
                return

        # CRITICAL FIX 4: Bulk Save jobs to database using the thread-local DB
        if jobs:
            logger.info(f"Saving {len(jobs)} jobs to database...")
            # Assuming JobDatabase.insert_jobs handles bulk transaction
            db.insert_jobs(jobs)

        # Step 2: Match jobs
        logger.info("\nStep 2: Matching jobs against resume...")
        high_matches: List[Tuple[Dict, Dict]] = [] 
        match_updates: List[Tuple[str, Dict]] = []

        # Use tqdm for progress tracking in the synchronous context
        for job in tqdm(jobs, desc="Matching jobs", unit="job"):
            match_result = self.matcher.match_job(job)
            match_updates.append((job["id"], match_result))

            score = match_result["match_score"]

            if score >= MATCH_THRESHOLD:
                high_matches.append((job, match_result))
                # Log high matches outside of tqdm for cleaner output
                logger.info(f" {job['title']} at {job['company']}: {score*100:.1f}% - HIGH MATCH")

        # CRITICAL FIX 5: Bulk update match scores using the thread-local DB
        if match_updates:
            db.bulk_update_match_scores(match_updates)
        
        logger.info(
            f"\nFound {len(high_matches)}/{len(jobs)} high matches (≥{MATCH_THRESHOLD*100}%)"
        )

        # Step 3: Tailor applications
        if not high_matches:
            logger.info(
                "No jobs met the match threshold. Try lowering MATCH_THRESHOLD in .env"
            )
            return

        logger.info("\nStep 3: Creating tailored applications...")

        if dry_run:
            logger.info("📝 DRY RUN: Skipping Gemini API calls")
            for job, match in high_matches:
                logger.info(f" Would tailor: {job['title']} at {job['company']}")
            return

        # Process with progress bar
        for job, match in tqdm(high_matches, desc="Tailoring applications", unit="job"):
            logger.info(f"\nTailoring for: {job['title']} at {job['company']}")

            try:
                # Correctly call the refactored tailoring methods
                job_description = job.get("description", "")
                resume_result = self.tailor.generate_tailored_resume(job_description)
                if not resume_result.success:
                    raise Exception(f"Resume tailoring failed: {resume_result.error}")

                summary_section = resume_result.tailored_content.split("## PROFESSIONAL SUMMARY")[1].split("##")[0].strip()
                cover_letter_result = self.tailor.generate_cover_letter(resume_result.analysis_obj, summary_section)

                application = {
                    "resume_text": resume_result.tailored_content,
                    "cover_letter": cover_letter_result.get("cover_letter", ""),
                    "changes": ["Automated tailoring complete."] # Placeholder
                }

                # Save to database
                db.save_application( # Use thread-local DB
                    job["id"],
                    application["resume_text"],
                    application["cover_letter"],
                    application["changes"],
                )

                # Save to files
                self._save_application_files(job, application)

                logger.info(" ✓ Application ready for review")

            except Exception as e:
                logger.error(f" ✗ Error tailoring application for {job['title']}: {e}")

        # Step 4: Show summary (Need a fresh DB instance for final stats)
        self._print_summary()

    def _save_application_files(self, job: Dict[str, Any], application: Dict[str, Any]) -> None:
        """Saves the tailored resume and cover letter to files."""
        try:
            # Sanitize company and title for filename
            company = "".join(c for c in job.get("company", "Unknown") if c.isalnum() or c in (" ", "_")).rstrip()
            title = "".join(c for c in job.get("title", "Job") if c.isalnum() or c in (" ", "_")).rstrip()

            # Create a unique directory for this application
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(f"output/{company}_{title}_{timestamp}")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save resume
            resume_path = output_dir / "tailored_resume.md"
            resume_path.write_text(application.get("resume_text", ""), encoding="utf-8")

            # Save cover letter
            cover_letter_path = output_dir / "cover_letter.txt"
            cover_letter_path.write_text(application.get("cover_letter", ""), encoding="utf-8")

            logger.info(f"✓ Saved application files to {output_dir}")
        except Exception as e:
            logger.error(f"Error saving application files for {job.get('title', 'N/A')}: {e}")


    # --- Helper Methods ---

    def _validate_job_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validates incoming dictionary data against expected job fields."""
        required_keys = ["title", "description"] 

        if not all(key in data and data[key] for key in required_keys):
            logger.warning(f"Skipping invalid job data: Missing required keys in {list(data.keys())}")
            return None

        valid_keys = ["title", "company", "url", "description", "location"]
        validated_job = {
            key: str(data.get(key, "")).strip()
            for key in valid_keys
        }
        
        return validated_job

    def add_manual_job(
        self,
        title: str,
        company: str = "Unknown",
        url: str = "",
        description: str = "",
        location: str = "",
    ) -> Dict[str, Any]:
        """
        Adds a job manually via the scraper's logic to generate a unique ID.
        """
        if not title.strip():
            raise ValueError("Job title cannot be empty")

        # Use the scraper to generate the ID/timestamping logic
        job = self.scraper.add_manual_job(title, company, url, description, location)
        return job
    
    # CRITICAL FIX 6: Modify DB calls in review_pending, _export_pending, approve_application, and _print_summary
    # to use a local DB instance or delegate to a thread-safe helper if necessary.
    
    def review_pending(self) -> None:
        """ Shows all applications that are pending review. """
        db = self.db_class() 
        pending = db.get_pending_reviews()

        if not pending:
            print("\nNo applications pending review.")
            return

        # ... (rest of review_pending logic remains the same)
        print("\n" + "=" * 80)
        print(f"PENDING REVIEW ({len(pending)} applications)")
        print("=" * 80 + "\n")

        for i, app in enumerate(pending, 1):
            # ... (rest of loop remains the same)
            print(f"{i}. {app['title']} at {app['company']}")
            print(f"   Match Score: {app['match_score']*100:.1f}%")
            print(f"   Location: {app['location']}")
            print(f"   URL: {app['url']}")

            try:
                # Use json.loads safely
                changes = json.loads(app.get("changes_summary", "[]") or "[]")
                print(f"   Changes: {', '.join(changes[:2])}")
            except json.JSONDecodeError:
                print(f"   Changes: Unable to parse changes")
            print()

        export = input("Export to CSV? [y/N]: ").strip().lower()
        if export == 'y':
            self._export_pending(pending)

    def _export_pending(self, pending: List[Dict[str, Any]]) -> None:
        """ Export pending applications to CSV """
        csv_file = Path("output/pending_applications.csv")
        csv_file.parent.mkdir(exist_ok=True)

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Title", "Company", "Match Score", "Location", "URL"])
            for app in pending:
                writer.writerow([
                    app['title'],
                    app['company'],
                    f"{app['match_score']*100:.1f}%",
                    app['location'],
                    app['url']
                ])

        logger.info(f"✓ Exported to {csv_file}")

    def approve_application(self, job_id: str) -> None:
        """
        Approves an application by updating its status in the database.
        """
        db = self.db_class() 
        db.update_status(job_id, "applied")
        logger.info(f"✓ Application approved: {job_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """Gets statistics from the database."""
        db = self.db_class()
        stats = db.get_statistics()
        return stats

    def run_interactive(self) -> None:
        """Runs the bot in an interactive mode for manual job entry."""
        print("\n" + "=" * 80)
        print("INTERACTIVE MODE: Manually Add a Job")
        print("=" * 80)

        try:
            title = input("Enter Job Title: ").strip()
            if not title:
                print("Job title is required.")
                return

            company = input("Enter Company Name: ").strip()
            description = ""
            print("Enter Job Description (type 'END' on a new line to finish):")
            while True:
                line = input()
                if line.strip() == 'END':
                    break
                description += line + "\n"

            if not description.strip():
                print("Job description is required.")
                return

            manual_job = self.add_manual_job(
                title=title,
                company=company,
                description=description
            )

            print("\nJob added. Starting pipeline in background...")
            self.run_pipeline_async(manual_jobs=[manual_job], dry_run=False)
            # In a CLI context, we might want to wait for this to finish.
            # For now, it runs in the background and the script will exit.

        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive mode.")


    # (Other helper functions remain the same)

    def _print_summary(self) -> None:
        """ Prints a summary of the pipeline's execution. """
        db = self.db_class()
        db.connect()
        stats = db.get_statistics()
        db.close()

        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Total Jobs: {stats['total_jobs']}")
        print(f"High Matches (≥{MATCH_THRESHOLD*100}%): {stats['high_matches']}")
        print(f"Applications Prepared: {stats['by_status'].get('pending_review', 0)}")
        print(f"Average Match Score: {stats['avg_match_score']*100:.1f}%")
        print("\nNext Steps:")
        print("1. Review applications: python main.py review")
        print("2. Check output/ folder for tailored resumes and cover letters")
        print("3. Open database with: sqlite3 data/job_applications.db")

        backup_file = create_backup()
        if backup_file:
            print(f"4. Database backed up to: {backup_file}")

        print("=" * 80 + "\n")

    def import_jobs(self, file_path: str) -> None:
        """Import jobs from JSON or CSV file and runs the pipeline."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return

        jobs = []
        try:
            if path.suffix.lower() == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    for job_data in raw_data:
                        if isinstance(job_data, dict):
                            validated_job = self._validate_job_data(job_data)
                            if validated_job:
                                jobs.append(self.add_manual_job(**validated_job))
            elif path.suffix.lower() == '.csv':
                with open(path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        validated_job = self._validate_job_data(row)
                        if validated_job:
                            jobs.append(self.add_manual_job(**validated_job))
            else:
                logger.error("Unsupported file format. Use JSON or CSV.")
                return
        except (json.JSONDecodeError, csv.Error) as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return

        logger.info(f"Successfully imported and validated {len(jobs)} jobs from {file_path}")
        
        if not jobs:
            logger.info("No valid jobs found in the file to process.")
            return

        # Execute pipeline and wait for it to complete
        print(f"Pipeline starting for {len(jobs)} imported jobs...")
        future = self.run_pipeline_async(manual_jobs=jobs, dry_run=False)
        future.result() # Block until the pipeline is complete
        print("Import and processing complete.")
        
    def _import_callback(self, future):
        """ Handles the result of the import pipeline task. """
        if future.exception():
            logger.error(f"Import pipeline failed: {future.exception()}")
        else:
            logger.info("Import pipeline finished successfully.")
            
    def export_jobs(self, output_file: str = "output/jobs_export.json") -> None:
        """ Export all jobs to JSON """
        db = self.db_class()
        all_jobs = db.get_all_jobs()
        
        with open(output_file, 'w') as f:
            json.dump(all_jobs, f, indent=2, default=str)
        logger.info(f"✓ Exported {len(all_jobs)} jobs to {output_file}")

    def tailor_for_gui(self, job_description: str, user_resume_text: str) -> Dict[str, Any]:
        """
        A dedicated method for the GUI to call for tailoring.
        It does not interact with the database.
        It generates a tailored resume and cover letter.
        """
        try:
            # We pass the user's potentially edited resume text to a new tailor instance
            temp_resume_data = self.tailor.resume.copy() # Start with base resume
            # This is a simplification; a real implementation would parse the text
            # and reconstruct the data structure. For now, we proceed with the base resume.
            tailor = ResumeTailor(resume_data=temp_resume_data)

            logger.info("GUI Tailoring: Generating tailored resume...")
            resume_result = tailor.generate_tailored_resume(job_description)
            if not resume_result.success:
                raise Exception(f"Resume tailoring failed: {resume_result.error}")

            logger.info("GUI Tailoring: Generating cover letter...")
            summary_section = resume_result.tailored_content.split("## PROFESSIONAL SUMMARY")[1].split("##")[0].strip()
            cover_letter_result = tailor.generate_cover_letter(resume_result.analysis_obj, summary_section)

            return {
                "resume_text": resume_result.tailored_content,
                "cover_letter": cover_letter_result.get("cover_letter", "Failed to generate."),
                "changes": ["GUI-based tailoring completed."]
            }
        except Exception as e:
            logger.exception("FATAL: GUI Tailoring process failed.")
            raise e

def main() -> None:
    """
    The main entry point for the Job Application Bot.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Job Application Bot")
    # ... (parser setup remains the same)
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", aliases=["i"], 
                                               help="Run in interactive mode (add jobs manually)")
    interactive_parser.add_argument("--dry-run", action="store_true", 
                                    help="Skip API calls for testing")

    # Review command
    review_parser = subparsers.add_parser("review", aliases=["r"], 
                                          help="Review pending applications")
    review_parser.add_argument("--export", action="store_true", 
                               help="Export pending applications to CSV")

    # Stats command
    stats_parser = subparsers.add_parser("stats", aliases=["s"], 
                                         help="Show statistics")
    stats_parser.add_argument("--export", type=str, metavar="FILENAME",
                              help="Export statistics to JSON file")

    # Import/Export commands
    import_parser = subparsers.add_parser("import", help="Import jobs from file")
    import_parser.add_argument("file", help="JSON or CSV file to import")

    export_parser = subparsers.add_parser("export", help="Export jobs to file")
    export_parser.add_argument("--output", default="output/jobs_export.json", 
                               help="Output file path")

    # Backup command
    subparsers.add_parser("backup", help="Create database backup")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\n" + "=" * 80)
        print("JOB APPLICATION BOT")
        # ... (rest of help message)
        print("=" * 80)
        print("\nExamples:")
        print("  python main.py interactive          # Add jobs interactively")
        print("  python main.py review               # Review pending applications")
        print("  python main.py stats                # Show statistics")
        print("  python main.py import jobs.json     # Import jobs from JSON")
        print("  python main.py export               # Export jobs to JSON")
        print("\n" + "=" * 80)
        sys.exit(0)

    bot = JobApplicationBot()

    try:
        # CLI commands using the bot's methods
        if args.command in ("interactive", "i"):
            bot.run_interactive()
        elif args.command in ("review", "r"):
            bot.review_pending()
        elif args.command in ("stats", "s"):
            stats = bot.get_statistics()
            
            print("\n=== STATISTICS ===")
            print(f"Total Jobs: {stats['total_jobs']}")
            print(f"High Matches: {stats['high_matches']}")
            print(f"Avg Match Score: {stats['avg_match_score']*100:.1f}%")
            print("\nBy Status:")
            for status, count in stats["by_status"].items():
                print(f"  {status}: {count}")

            if hasattr(args, 'export') and args.export:
                with open(args.export, 'w') as f:
                    json.dump(stats, f, indent=2, default=str)
                print(f"\n✓ Exported to {args.export}")
        elif args.command == "import":
            bot.import_jobs(args.file)
        elif args.command == "export":
            bot.export_jobs(args.output)
        elif args.command == "backup":
            backup_file = create_backup()
            if backup_file:
                print(f"✓ Database backed up to: {backup_file}")
            else:
                print("❌ Backup failed")

    except Exception as e:
        logger.exception("Fatal error in main execution")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

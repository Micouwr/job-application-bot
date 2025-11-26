#!/usr/bin/env python3
"""
Job Application Bot - Main Entry Point
Author: Ryan Micou
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

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
from database import JobDatabase, create_backup
from matcher import JobMatcher
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

    This class initializes all the necessary components (database, scraper, matcher, tailor)
    and provides methods to run the job application pipeline, either interactively or as a library.
    """

    def __init__(self) -> None:
        """Initializes the JobApplicationBot."""
        logger.info("=" * 80)
        logger.info("Job Application Bot Starting")
        logger.info("=" * 80)

        # Initialize components
        self.db = JobDatabase()
        self.scraper = JobScraper()
        self.matcher = JobMatcher()
        self.tailor = ResumeTailor(RESUME_DATA)
        
        # Initialize job board integrations if API key is available
        if config.scraper_api_key:
            self.job_boards = JobBoardIntegration(config.scraper_api_key)
        else:
            self.job_boards = None
            logger.info("ℹ️ No ScraperAPI key found. Manual job entry only.")

        logger.info("✓ All components initialized")

    def run_pipeline(self, manual_jobs: Optional[List[Dict]] = None, dry_run: bool = False) -> None:
        """
        Runs the complete job application pipeline.
        
        Args:
            manual_jobs: A list of job dictionaries to process
            dry_run: If True, process everything except Gemini API calls
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
                jobs = self.job_boards.scrape_all(
                    keywords=JOB_KEYWORDS,
                    location=JOB_LOCATION,
                    max_jobs=MAX_JOBS_PER_PLATFORM
                )
                logger.info(f"Scraped {len(jobs)} jobs from job boards")
            else:
                logger.warning("Automated scraping not configured. Use --interactive mode.")
                return

        # Save jobs to database
        logger.info(f"Saving {len(jobs)} jobs to database...")
        for job in jobs:
            self.db.insert_job(job)

        # Step 2: Match jobs
        logger.info("\nStep 2: Matching jobs against resume...")
        high_matches: List[Dict] = []

        for job in jobs:
            match_result = self.matcher.match_job(job)
            self.db.update_match_score(job["id"], match_result)

            score = match_result["match_score"]
            logger.info(f" {job['title']} at {job['company']}: {score*100:.1f}%")

            if score >= MATCH_THRESHOLD:
                high_matches.append((job, match_result))
                logger.info(f" ✓ HIGH MATCH - {match_result['recommendation']}")

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

                logger.info(" ✓ Application ready for review")

            except Exception as e:
                logger.error(f" ✗ Error tailoring application: {e}")

        # Step 4: Show summary
        self._print_summary()

    def add_manual_job(
        self,
        title: str,
        company: str = "Unknown",
        url: str = "",
        description: str = "",
        location: str = "",
    ) -> Dict[str, Any]:
        """
        Adds a job manually.

        Args:
            title: The title of the job.
            company: The name of the company.
            url: The URL of the job posting.
            description: The full job description.
            location: The location of the job.

        Returns:
            A dictionary representing the job.
        """
        if not title.strip():
            raise ValueError("Job title cannot be empty")
            
        job = self.scraper.add_manual_job(title, company, url, description, location)
        logger.info(f"✓ Added: {title} at {company}")
        return job

    def run_interactive(self) -> None:
        """  Runs the bot in interactive mode, allowing the user to add jobs one by one. """
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
                print("❌ Job title cannot be empty. Please try again.")
                continue

            company = input("Company: ").strip()
            if not company:
                company = "Unknown"
                print("ℹ️ Using default company: Unknown")

            location = input(f"Location [{JOB_LOCATION}]: ").strip() or JOB_LOCATION
            url = input("Job URL (optional): ").strip()

            print("\nPaste job description (press Enter twice when done):")
            description_lines = []
            while True:
                line = input()
                if line == "":
                    break
                description_lines.append(line)
            description = "\n".join(description_lines)

            try:
                job = self.add_manual_job(title, company, url, description, location)
                jobs.append(job)
                print(f"\n✓ Added {title} at {company}")
            except ValueError as e:
                print(f"❌ Error: {e}")

        if jobs:
            # Ask for confirmation before processing
            confirm = input(f"\nProcess {len(jobs)} jobs? [Y/n]: ").strip().lower()
            if confirm in ('', 'y', 'yes'):
                dry_run = input("Dry run (skip API calls)? [y/N]: ").strip().lower() == 'y'
                logger.info(f"\nProcessing {len(jobs)} jobs...")
                self.run_pipeline(manual_jobs=jobs, dry_run=dry_run)
            else:
                logger.info("Processing cancelled.")
        else:
            logger.info("No jobs added.")

    def review_pending(self) -> None:
        """ Shows all applications that are pending review. """
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

            try:
                changes = (
                    json.loads(app["changes_summary"]) if app["changes_summary"] else []
                )
                print(f"   Changes: {', '.join(changes[:2])}")
            except (json.JSONDecodeError, TypeError):
                print(f"   Changes: Unable to parse changes")
            print()

        # Option to export
        export = input("Export to CSV? [y/N]: ").strip().lower()
        if export == 'y':
            self._export_pending(pending)

    def _export_pending(self, pending: List[Dict[str, Any]]) -> None:
        """  Export pending applications to CSV """
        import csv
        
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

        Args:
            job_id: The ID of the job to approve.
        """
        self.db.update_status(job_id, "applied")
        logger.info(f"✓ Application approved: {job_id}")

    def _save_application_files(self, job: Dict[str, Any], application: Dict[str, Any]) -> None:
        """
        Saves the tailored resume and cover letter to files.

        Args:
            job: The job dictionary.
            application: The application dictionary, containing the resume and cover letter.
        """
        try:
            safe_company = "".join(
                c for c in job["company"] if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            timestamp = datetime.now().strftime("%Y%m%d")

            resume_file = RESUMES_DIR / f"{safe_company}_{timestamp}_resume.txt"
            resume_file.parent.mkdir(parents=True, exist_ok=True)
            with open(resume_file, "w", encoding="utf-8") as f:
                f.write(application["resume_text"])

            cover_file = COVER_LETTERS_DIR / f"{safe_company}_{timestamp}_cover_letter.txt"
            cover_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cover_file, "w", encoding="utf-8") as f:
                f.write(application["cover_letter"])

            logger.info(f"   Saved to: {resume_file.name} and {cover_file.name}")
        except OSError as e:  # ✅ Fixed: OSError instead of IOError
            logger.error(f"   Failed to save application files: {e}")

    def _print_summary(self) -> None:
        """  Prints a summary of the pipeline's execution. """
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
        
        # Add backup reminder
        backup_file = create_backup()
        if backup_file:
            print(f"4. Database backed up to: {backup_file}")
        
        print("=" * 80 + "\n")

    def import_jobs(self, file_path: str) -> None:
        """Import jobs from JSON or CSV file"""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return

        jobs = []
        if path.suffix.lower() == '.json':
            with open(path, 'r') as f:
                jobs = json.load(f)
        elif path.suffix.lower() == '.csv':
            import csv
            with open(path, 'r') as f:
                reader = csv.DictReader(f)
                jobs = list(reader)
        else:
            logger.error("Unsupported file format. Use JSON or CSV.")
            return

        logger.info(f"Importing {len(jobs)} jobs from {file_path}")
        self.run_pipeline(manual_jobs=jobs)

    def export_jobs(self, output_file: str = "output/jobs_export.json") -> None:
        """  Export all jobs to JSON """
        all_jobs = self.db.get_all_jobs()
        with open(output_file, 'w') as f:
            json.dump(all_jobs, f, indent=2, default=str)
        logger.info(f"✓ Exported {len(all_jobs)} jobs to {output_file}")


def main() -> None:
    """
    The main entry point for the Job Application Bot.

    Uses enhanced CLI with subcommands for better organization.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Job Application Bot")
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
        print("=" * 80)
        print("\nExamples:")
        print("  python main.py interactive          # Add jobs interactively")
        print("  python main.py review               # Review pending applications")
        print("  python main.py stats                # Show statistics")
        print("  python main.py import jobs.json     # Import jobs from JSON")
        print("\n" + "=" * 80)
        sys.exit(0)

    bot = JobApplicationBot()

    try:
        if args.command in ("interactive", "i"):
            bot.run_interactive()
        elif args.command in ("review", "r"):
            bot.review_pending()
        elif args.command in ("stats", "s"):
            stats = bot.db.get_statistics()
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

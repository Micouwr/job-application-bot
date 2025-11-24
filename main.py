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
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config.settings as settings
from database import JobDatabase
from matcher import JobMatcher
from scraper import JobScraper
from tailor import ResumeTailor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(settings.LOG_FILE), logging.StreamHandler()],
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

        # Validate configuration
        try:
            settings.validate_config()
            logger.info("✓ Configuration validated")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

        # Initialize components
        self.db = JobDatabase()
        self.scraper = JobScraper()
        self.matcher = JobMatcher()
        self.tailor = ResumeTailor(settings.RESUME_DATA)

        logger.info("✓ All components initialized")

    def run_pipeline(self, manual_jobs: Optional[List[Dict]] = None) -> None:
        """
        Runs the complete job application pipeline.

        Args:
            manual_jobs: A list of job dictionaries to process. If not provided,
                         the method will attempt to scrape jobs (which is not yet implemented).
        """
        logger.info("\n" + "=" * 80)
        logger.info("STARTING PIPELINE")
        logger.info("=" * 80 + "\n")

        # Step 1: Get jobs
        if manual_jobs:
            jobs = manual_jobs
            logger.info(f"Using {len(jobs)} manually added jobs")
        else:
            logger.info("Step 1: Scraping jobs...")
            logger.warning("Automated scraping not implemented yet.")
            logger.info("Please use add_manual_job() or run in interactive mode")
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
            logger.info(f"  {job['title']} at {job['company']}: {score*100:.1f}%")

            if score >= settings.MATCH_THRESHOLD:
                high_matches.append((job, match_result))
                logger.info(f"    ✓ HIGH MATCH - {match_result['recommendation']}")

        logger.info(
            f"\nFound {len(high_matches)}/{len(jobs)} high matches (≥{settings.MATCH_THRESHOLD*100}%)"
        )

        # Step 3: Tailor applications
        if not high_matches:
            logger.info(
                "No jobs met the match threshold. Try lowering MATCH_THRESHOLD in .env"
            )
            return

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

                logger.info("  ✓ Application ready for review")

            except Exception as e:
                logger.error(f"  ✗ Error tailoring application for {job['title']} ({job['id']}): {e}")

        # Step 4: Show summary
        self._print_summary()

    def add_manual_job(
        self,
        title: str,
        company: str = "Unknown",
        url: str = "",
        description: str = "",
        location: str = "",
    ) -> Dict:
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
        job = self.scraper.add_manual_job(title, company, url, description, location)
        logger.info(f"✓ Added: {title} at {company}")
        return job

    def run_interactive(self) -> None:
        """Runs the bot in interactive mode, allowing the user to add jobs one by one."""
        logger.info("\n" + "=" * 80)
        logger.info("INTERACTIVE MODE")
        logger.info("=" * 80 + "\n")

        jobs: List[Dict] = []

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
                print("ℹ️  Using default company: Unknown")

            url = input("Job URL: ").strip()
            location = input(f"Location [{settings.JOB_LOCATION}]: ").strip() or settings.JOB_LOCATION

            print("\nPaste job description (press Enter twice when done):")
            description_lines = []
            while True:
                line = input()
                if not line.strip():
                    break
                description_lines.append(line)
            description = "\n".join(description_lines)

            job = self.add_manual_job(title, company, url, description, location)
            jobs.append(job)

            print(f"\n✓ Added {title} at {company}")

        if jobs:
            logger.info(f"\nProcessing {len(jobs)} jobs...")
            self.run_pipeline(manual_jobs=jobs)
        else:
            logger.info("No jobs added.")

    def review_pending(self) -> None:
        """Shows all applications that are pending review."""
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
            except json.JSONDecodeError:
                changes = []
                logger.warning(f"Invalid JSON in changes_summary for {app['title']}")

            print(f"   Changes: {', '.join(changes[:2])}")
            print()

    def approve_application(self, job_id: str) -> None:
        """
        Approves an application by updating its status in the database.

        Args:
            job_id: The ID of the job to approve.
        """
        self.db.update_status(job_id, "applied")
        logger.info(f"✓ Application approved: {job_id}")

    def approve_interactive(self) -> None:
        """Runs an interactive session to approve pending applications."""
        pending = self.db.get_pending_reviews()

        if not pending:
            print("\nNo applications pending review.")
            return

        while True:
            print("\n" + "=" * 80)
            print("INTERACTIVE APPROVAL")
            print("=" * 80 + "\n")

            for i, app in enumerate(pending, 1):
                score = app['match_score'] or 0
                print(f"[{i}] {app['title']} at {app['company']} ({score*100:.1f}%)")

            print("\nEnter number to approve, 'all', or 'quit'.")
            choice = input("> ").strip().lower()

            if choice == 'quit':
                break
            elif choice == 'all':
                for app in pending:
                    self.approve_application(app['id'])
                print("\n✅ All pending applications approved.")
                break
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(pending):
                        job_id = pending[index]['id']
                        self.approve_application(job_id)
                        # Refresh list
                        pending = self.db.get_pending_reviews()
                        if not pending:
                            break
                    else:
                        print("❌ Invalid number. Please try again.")
                except ValueError:
                    print("❌ Invalid input. Please enter a number, 'all', or 'quit'.")

    def _save_application_files(self, job: Dict, application: Dict) -> None:
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
            safe_title = "".join(
                c for c in job["title"] if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            timestamp = datetime.now().strftime("%Y%m%d")

            base_filename = f"{safe_company}_{safe_title}_{timestamp}"

            resume_file = settings.RESUMES_DIR / f"{base_filename}_resume.txt"
            resume_file.parent.mkdir(parents=True, exist_ok=True)
            with open(resume_file, "w", encoding="utf-8") as f:
                f.write(application["resume_text"])

            cover_file = settings.COVER_LETTERS_DIR / f"{base_filename}_cover_letter.txt"
            cover_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cover_file, "w", encoding="utf-8") as f:
                f.write(application["cover_letter"])

            logger.info(f"  Saved to: {resume_file.name} and {cover_file.name}")
        except IOError as e:
            logger.error(f"  Failed to save application files: {e}")

    def _print_summary(self) -> None:
        """Prints a summary of the pipeline's execution."""
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
    The main entry point for the Job Application Bot.

    Parses command-line arguments and runs the bot in the specified mode.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Job Application Bot")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode (add jobs manually)",
    )
    parser.add_argument(
        "--review", "-r", action="store_true", help="Review pending applications"
    )
    parser.add_argument(
        "--approve", "-a", action="store_true", help="Interactively approve applications"
    )
    parser.add_argument("--stats", "-s", action="store_true", help="Show statistics")

    args = parser.parse_args()

    bot = JobApplicationBot()

    if args.interactive:
        bot.run_interactive()
    elif args.review:
        bot.review_pending()
    elif args.approve:
        bot.approve_interactive()
    elif args.stats:
        stats = bot.db.get_statistics()
        print("\n=== STATISTICS ===")
        print(f"Total Jobs: {stats['total_jobs']}")
        print(f"High Matches: {stats['high_matches']}")
        print(f"Avg Match Score: {stats['avg_match_score']*100:.1f}%")
        print("\nBy Status:")
        for status, count in stats["by_status"].items():
            print(f"  {status}: {count}")
    else:
        # Default: Show usage
        print("\n" + "=" * 80)
        print("JOB APPLICATION BOT")
        print("=" * 80)
        print("\nUsage:")
        print("  python main.py --interactive    # Add jobs interactively")
        print("  python main.py --review         # Review pending applications")
        print("  python main.py --stats          # Show statistics")
        print("\nOr use as a library:")
        print("  from main import JobApplicationBot")
        print("  bot = JobApplicationBot()")
        print("  bot.add_manual_job(...)")
        print("  bot.run_pipeline()")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

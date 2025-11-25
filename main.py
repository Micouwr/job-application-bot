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

from config.settings import (COVER_LETTERS_DIR, JOB_KEYWORDS, JOB_LOCATION,
                             LOG_FILE, MATCH_THRESHOLD, MAX_JOBS_PER_PLATFORM,
                             RESUME_DATA, RESUMES_DIR, validate_config)
from database import JobDatabase
from matcher import JobMatcher
from scraper import JobScraper
from tailor import ResumeTailor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
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

        # Validate configuration
        try:
            validate_config()
            logger.info("✓ Configuration validated")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            print(f"\n❌ Configuration Error: {e}")
            sys.exit(1)

        # Initialize components
        self.db = JobDatabase()
        self.scraper = JobScraper()
        self.matcher = JobMatcher()
        self.tailor = ResumeTailor(RESUME_DATA)

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
            logger.info(f"Using {len(manual_jobs)} manually added jobs")
        else:
            logger.info("Step 1: Scraping jobs...")
            logger.warning("Automated scraping not implemented yet.")
            logger.info("Please use add_manual_job() or run in interactive mode")
            return

        # Save jobs to database
        logger.info(f"Saving {len(jobs)} jobs to database...")
        successful_inserts = 0
        for job in jobs:
            try:
                result = self.db.insert_job(job)
                if result:
                    successful_inserts += 1
            except Exception as e:
                logger.error(f"Failed to insert job {job.get('title', 'Unknown')}: {e}")
        
        logger.info(f"✓ Successfully saved {successful_inserts}/{len(jobs)} jobs")

        # Step 2: Match jobs
        logger.info("\nStep 2: Matching jobs against resume...")
        high_matches: List[Dict] = []

        for job in jobs:
            try:
                match_result = self.matcher.match_job(job)
                self.db.update_match_score(job["id"], match_result)

                score = match_result["match_score"]
                logger.info(f"  {job['title']} at {job['company']}: {score*100:.1f}%")

                if score >= MATCH_THRESHOLD:
                    high_matches.append((job, match_result))
                    logger.info(f"    ✓ HIGH MATCH - {match_result['recommendation']}")
            except Exception as e:
                logger.error(f"  ✗ Error matching job {job['id']}: {e}")

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
                logger.error(f"  ✗ Error tailoring application: {e}")

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
        try:
            job = self.scraper.add_manual_job(title, company, url, description, location)
            logger.info(f"✓ Added: {title} at {company}")
            return job
        except Exception as e:
            logger.error(f"Failed to add manual job: {e}")
            raise

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

            url = input("Job URL (optional): ").strip()
            location = input(f"Location [{JOB_LOCATION}]: ").strip() or JOB_LOCATION

            print("\nPaste job description (press Enter on empty line when done):")
            description_lines = []
            while True:
                line = input()
                if line == "":
                    # Break after first empty line for better UX
                    break
                description_lines.append(line)
            description = "\n".join(description_lines)

            try:
                job = self.add_manual_job(title, company, url, description, location)
                jobs.append(job)
                print(f"\n✓ Added {title} at {company}")
            except ValueError as e:
                print(f"\n❌ Error adding job: {e}")
                continue
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                logger.error(f"Error in interactive job entry: {e}")
                continue

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
            
            # Safely handle missing match_score
            score = app.get("match_score", 0)
            if isinstance(score, (int, float)):
                print(f"   Match Score: {score*100:.1f}%")
            else:
                print(f"   Match Score: N/A")
            
            print(f"   Location: {app.get('location', 'Unknown')}")
            print(f"   URL: {app.get('url', 'No URL')}")

            # Safely parse changes
            try:
                changes = (
                    json.loads(app["changes_summary"]) if app.get("changes_summary") else []
                )
            except (json.JSONDecodeError, TypeError):
                changes = []
                logger.warning(f"Invalid JSON in changes_summary for {app.get('title', 'Unknown')}")

            if changes:
                print(f"   Changes: {', '.join(changes[:2])}")
            print()

    def approve_application(self, job_id: str) -> None:
        """
        Approves an application by updating its status in the database.

        Args:
            job_id: The ID of the job to approve.
        """
        try:
            result = self.db.update_status(job_id, "applied")
            if result:
                logger.info(f"✓ Application approved: {job_id}")
            else:
                logger.warning(f"Job ID not found: {job_id}")
        except Exception as e:
            logger.error(f"Error approving application: {e}")
            raise

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
                score = app.get("match_score", 0)
                if isinstance(score, (int, float)):
                    print(f"[{i}] {app['title']} at {app['company']} ({score*100:.1f}%)")
                else:
                    print(f"[{i}] {app['title']} at {app['company']} (N/A)")

            print("\nEnter number to approve, 'all', or 'quit'.")
            choice = input("> ").strip().lower()

            if choice == "quit":
                break
            elif choice == "all":
                approved_count = 0
                for app in pending:
                    try:
                        self.approve_application(app["id"])
                        approved_count += 1
                    except Exception as e:
                        logger.error(f"Failed to approve {app['id']}: {e}")
                
                print(f"\n✅ Approved {approved_count} applications.")
                break
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(pending):
                        job_id = pending[index]["id"]
                        self.approve_application(job_id)
                        # Refresh list
                        pending = self.db.get_pending_reviews()
                        if not pending:
                            print("\n✅ No more pending applications.")
                            break
                    else:
                        print("❌ Invalid number. Please try again.")
                except ValueError:
                    print("❌ Invalid input. Please enter a number, 'all', or 'quit'.")
                except Exception as e:
                    logger.error(f"Error in approval: {e}")
                    print(f"❌ Error: Could not approve application.")

    def _save_application_files(self, job: Dict, application: Dict) -> None:
        """
        Saves the tailored resume and cover letter to files.

        Args:
            job: The job dictionary.
            application: The application dictionary, containing the resume and cover letter.
        """
        try:
            # BUG FIX #1: Prevent empty filenames
            safe_company = "".join(
                c for c in job["company"] if c.isalnum() or c in ("-", "_", " ")
            ).strip()
            
            # CRITICAL: Fallback if sanitization results in empty string
            if not safe_company:
                safe_company = f"JOB_{job['id'][-8:]}"
                logger.warning(f"Empty company name after sanitization, using fallback: {safe_company}")
            
            # Limit length to prevent filesystem errors
            safe_company = safe_company[:30]
            
            timestamp = datetime.now().strftime("%Y%m%d")

            # Create directories if they don't exist
            RESUMES_DIR.mkdir(parents=True, exist_ok=True)
            COVER_LETTERS_DIR.mkdir(parents=True, exist_ok=True)

            # Save files
            resume_file = RESUMES_DIR / f"{safe_company}_{timestamp}_resume.txt"
            with open(resume_file, "w", encoding="utf-8") as f:
                f.write(application["resume_text"])

            cover_file = COVER_LETTERS_DIR / f"{safe_company}_{timestamp}_cover_letter.txt"
            with open(cover_file, "w", encoding="utf-8") as f:
                f.write(application["cover_letter"])

            logger.info(f"  ✓ Saved: {resume_file.name}")
            logger.info(f"  ✓ Saved: {cover_file.name}")
            
        except IOError as e:
            logger.error(f"  ✗ Failed to save files: {e}")
            # Don't crash the pipeline - log error and continue
        except Exception as e:
            logger.error(f"  ✗ Unexpected error saving files: {e}")

    def _print_summary(self) -> None:
        """Prints a summary of the pipeline's execution."""
        try:
            stats = self.db.get_statistics()
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            print("\n❌ Error: Could not generate summary")
            return
        
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        print(f"Total Jobs: {stats.get('total_jobs', 'N/A')}")
        print(f"High Matches (≥{MATCH_THRESHOLD*100:.0f}%): {stats.get('high_matches', 'N/A')}")
        
        # Safe stats display
        by_status = stats.get('by_status', {})
        if isinstance(by_status, dict):
            pending = by_status.get('pending_review', 0)
        else:
            pending = 0
        print(f"Applications Prepared: {pending}")
        
        avg_score = stats.get('avg_match_score', 0)
        if isinstance(avg_score, (int, float)) and avg_score > 0:
            print(f"Average Match Score: {avg_score*100:.1f}%")
        else:
            print("Average Match Score: N/A")
        
        print("\nNext Steps:")
        print("1. Review applications: python main.py --review")
        print("2. Check output/ folder for tailored resumes and cover letters")
        print("3. Approve applications: python main.py --approve")
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
        "--approve", "-a", action="store_true", help="Approve applications interactively"
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
        avg_score = stats['avg_match_score']
        if avg_score > 0:
            print(f"Avg Match Score: {avg_score*100:.1f}%")
        else:
            print("Avg Match Score: N/A")
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
        print("  python main.py --approve        # Approve applications")
        print("  python main.py --stats          # Show statistics")
        print("\nOr use as a library:")
        print("  from main import JobApplicationBot")
        print("  bot = JobApplicationBot()")
        print("  bot.add_manual_job(...)")
        print("  bot.run_pipeline()")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

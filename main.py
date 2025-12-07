#!/usr/bin/env python3
"""
Job Application Bot - Main Entry Point (Scraper Removed - Manual Only)
Author: Ryan Micou
"""

import json
import logging
import sys
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from tqdm import tqdm

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
from tailor import ResumeTailor

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class JobApplicationBot:
    def __init__(self) -> None:
        logger.info("=" * 80)
        logger.info("Job Application Bot Starting - Manual Mode Only")
        logger.info("=" * 80)

        self.db_class = JobDatabase
        self.matcher = JobMatcher(RESUME_DATA)
        self.tailor = ResumeTailor(RESUME_DATA)
        self.executor = ThreadPoolExecutor(max_workers=5)

        logger.info("All components initialized (no web scraping)")

    def run_pipeline_async(self, manual_jobs: Optional[List[Dict]] = None, dry_run: bool = False, callback: Optional[Callable] = None):
        future = self.executor.submit(self._pipeline_task, manual_jobs or [], dry_run)
        if callback:
            future.add_done_callback(lambda f: callback(f.result()))
        return future

    def _pipeline_task(self, jobs: List[Dict], dry_run: bool) -> bool:
        db = self.db_class()
        try:
            db.connect()
            self.run_pipeline(db, jobs, dry_run=dry_run)
            return True
        except Exception as e:
            logger.exception("Pipeline failed")
            return False
        finally:
            try:
                db.close()
            except:
                pass

    def run_pipeline(self, db: JobDatabase, jobs: List[Dict], dry_run: bool = False) -> None:
        logger.info(f"Processing {len(jobs)} manually added jobs")

        if jobs:
            db.insert_jobs(jobs)

        high_matches = []
        for job in tqdm(jobs, desc="Matching jobs", unit="job"):
            match_result = self.matcher.match_job(job)
            score = match_result["match_score"]
            db.update_match_score(job["id"], score, match_result)

            if score >= MATCH_THRESHOLD:
                high_matches.append((job, match_result))
                logger.info(f" HIGH MATCH: {job['title']} at {job.get('company', 'Unknown')} - {score:.1%}")

        logger.info(f"Found {len(high_matches)} high matches")

        if not high_matches:
            logger.info("No high matches. Try lowering MATCH_THRESHOLD in .env")
            return

        if dry_run:
            logger.info("DRY RUN: Skipping AI tailoring")
            return

        for job, match in tqdm(high_matches, desc="Tailoring applications", unit="job"):
            try:
                result = self.tailor.generate_tailored_resume(
                    job_description=job.get("description", "") + job.get("requirements", ""),
                    job_title=job.get("title", ""),
                    company=job.get("company", "")
                )
                if result.success:
                    db.save_application(job["id"], result)
                    logger.info(f" Tailored: {job['title']}")
            except Exception as e:
                logger.error(f" Failed to tailor {job['title']}: {e}")

        self._print_summary(db)

    def _print_summary(self, db: JobDatabase):
        try:
            db.connect()
            stats = db.get_statistics()
            print("\n" + "="*60)
            print("PIPELINE COMPLETE")
            print("="*60)
            print(f"Total Jobs Processed: {stats['total_jobs']}")
            print(f"High Matches: {stats['high_matches']}")
            print(f"Applications Ready: {stats['by_status'].get('pending_review', 0)}")
            print("\nNext: Run `python main.py review` or open the GUI")
        finally:
            try:
                db.close()
            except:
                pass

    def add_manual_job(self, title: str, company: str = "", description: str = "", **kwargs) -> Dict:
        job = {
            "id": f"manual_{int(datetime.now().timestamp())}",
            "title": title,
            "company": company or "Unknown Company",
            "description": description,
            "url": kwargs.get("url", ""),
            "location": kwargs.get("location", ""),
            "date_added": datetime.now().isoformat()
        }
        return job


def main():
    bot = JobApplicationBot()
    print("Job Application Bot - Manual Mode")
    print("Paste jobs manually or import from CSV/JSON")
    print("Type 'help' for commands\n")

    while True:
        try:
            cmd = input("> ").strip()
            if cmd in ["quit", "exit", "q"]:
                break
            elif cmd == "help":
                print("add - Add a job manually")
                print("import <file> - Import from CSV/JSON")
                print("run - Process all jobs")
                print("gui - Launch GUI")
            elif cmd == "gui":
                from app.gui import start_gui
                start_gui()
                break
            elif cmd.startswith("import "):
                path = cmd[7:].strip()
                # Simple import stub - expand later
                print(f"Import from {path} not yet implemented")
            elif cmd == "add":
                title = input("Job Title: ")
                company = input("Company (optional): ")
                desc = input("Job Description (paste, then Ctrl+D/Ctrl+Z):\n")
                job = bot.add_manual_job(title, company, desc)
                bot.run_pipeline_async([job], dry_run=False)
                print("Job added and processing started")
            elif cmd == "run":
                bot.run_pipeline_async([], dry_run=False)
            else:
                print("Unknown command. Type 'help'")
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    main()
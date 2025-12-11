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
from app.tailor import ResumeTailor, TailoringResult

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

    def process_and_tailor_from_gui(self, job: Dict, user_resume_text: str) -> Dict:
        logger.info(f"Starting GUI-based tailoring for: {job.get('title', 'Unknown')}")
        temp_resume_data = RESUME_DATA.copy()
        temp_resume_data["summary"] = user_resume_text
        matcher = JobMatcher(temp_resume_data)
        tailor = ResumeTailor(temp_resume_data)
        try:
            result = tailor.generate_tailored_resume(
                job_description=job.get("description", ""),
                job_title=job.get("title", ""),
                company=job.get("company", "")
            )
            if result.success and result.tailored_content:
                parts = result.tailored_content.split("---")
                resume_text = parts[0].replace("# TAILORED RESUME", "").strip()
                cover_letter_text = parts[1].replace("# COVER LETTER", "").strip() if len(parts) > 1 else ""
                return {"resume_text": resume_text, "cover_letter": cover_letter_text, "success": True}
            else:
                raise Exception(result.error or "Unknown error")
        except Exception as e:
            logger.error(f"Failed: {e}")
            return {"resume_text": "", "cover_letter": "", "success": False, "error": str(e)}


def main():
    bot = JobApplicationBot()
    print("Job Application Bot - Manual Mode\n")
    while True:
        try:
            cmd = input("> ").strip()
            if cmd in ["quit", "exit", "q"]: break
            elif cmd == "help": print("\nCommands: add, import <file>, run, gui, quit\n")
            elif cmd == "gui":
                try:
                    from gui.tkinter_app import main as gui_main
                    gui_main()
                except Exception as e: print(f" GUI failed: {e}")
                break
            elif cmd.startswith("import "):
                path = cmd[7:].strip()
                try: print(f"Import from {path} not yet implemented")
                except FileNotFoundError: print(f" File not found: {path}")
                except Exception as e: print(f" Import failed: {e}")
            elif cmd == "add":
                try:
                    title = input("Job Title: ").strip()
                    if not title: print(" Title required"); continue
                    company = input("Company (optional): ").strip()
                    print("Description (Ctrl+D/Z to finish):")
                    desc = "\n".join(iter(input, "")).strip()
                    if not desc: print(" Description required"); continue
                    job = bot.add_manual_job(title, company, desc)
                    bot.run_pipeline_async([job], dry_run=False)
                    print(" Job added")
                except Exception as e: print(f" Add failed: {e}")
            elif cmd == "run":
                try: bot.run_pipeline_async([], dry_run=False); print(" Pipeline started")
                except Exception as e: print(f" Run failed: {e}")
            else: print(f" Unknown: '{cmd}'. Type 'help'")
        except (EOFError, KeyboardInterrupt): print("\n Goodbye!"); break
        except Exception as e: logger.exception(f"CLI error: {e}"); print(f"\n Error: {e}")


if __name__ == "__main__":
    main()
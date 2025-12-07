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
import time

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
from database import JobDatabase, create_backup, JobNotFoundError
from matcher import JobMatcher
from scraper import JobScraper, JobBoardIntegration
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
        logger.info("Job Application Bot Starting")
        logger.info("=" * 80)

        self.db_class = JobDatabase
        self.scraper = JobScraper()
        self.matcher = JobMatcher(RESUME_DATA)
        self.tailor = ResumeTailor(RESUME_DATA)

        if config.scraper_api_key:
            self.job_boards = JobBoardIntegration(config.scraper_api_key)
        else:
            self.job_boards = None
            logger.info("No ScraperAPI key found. Manual job entry or local scraper only.")

        self.executor = ThreadPoolExecutor(max_workers=5)
        logger.info("All components initialized")

    def run_pipeline_async(self, manual_jobs: Optional[List[Dict]] = None, dry_run: bool = False, callback: Optional[Callable] = None) -> None:
        future = self.executor.submit(self._pipeline_task, manual_jobs, dry_run)
        if callback:
            future.add_done_callback(lambda f: callback(f.result()))
        return future

    def _pipeline_task(self, manual_jobs: Optional[List[Dict]], dry_run: bool) -> bool:
        db = self.db_class()
        try:
            db.connect()
            self.run_pipeline(db, manual_jobs=manual_jobs, dry_run=dry_run)
            return True
        except Exception as e:
            logger.exception("FATAL: Pipeline task failed.")
            return False
        finally:
            try:
                db.close()
            except:
                pass

    def run_pipeline(self, db: JobDatabase, manual_jobs: Optional[List[Dict]] = None, dry_run: bool = False) -> None:
        # ... [rest of pipeline unchanged] ...
        # Only showing the parts that needed fixing for brevity
        pass  # Your existing pipeline code stays here

    def review_pending(self) -> None:
        db = self.db_class()
        try:
            db.connect()
            pending = db.get_pending_reviews()
            # ... existing logic ...
        finally:
            try:
                db.close()
            except:
                pass

    def _print_summary(self) -> None:
        db = self.db_class()
        try:
            db.connect()
            stats = db.get_statistics()
            # ... existing print logic ...
        finally:
            try:
                db.close()
            except:
                pass

    def approve_application(self, job_id: str) -> None:
        db = self.db_class()
        try:
            db.connect()
            db.update_status(job_id, "applied")
            logger.info(f"Application approved: {job_id}")
        finally:
            try:
                db.close()
            except:
                pass

    def export_jobs(self, output_file: str = "output/jobs_export.json") -> None:
        db = self.db_class()
        try:
            db.connect()
            all_jobs = db.get_all_jobs()
            with open(output_file, 'w') as f:
                json.dump(all_jobs, f, indent=2, default=str)
            logger.info(f"Exported {len(all_jobs)} jobs to {output_file}")
        finally:
            try:
                db.close()
            except:
                pass

    # ... rest of your methods (import_jobs, etc.) remain unchanged ...

def main() -> None:
    import argparse
    # ... your existing argparse and CLI logic ...
    pass

if __name__ == "__main__":
    main()
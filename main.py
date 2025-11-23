#!/usr/bin/env python3
"""
Job Application Bot - Main Entry Point
Author: Ryan Micou
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple   # <-- added this import

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    validate_config, JOB_KEYWORDS, JOB_LOCATION, 
    MAX_JOBS_PER_PLATFORM, MATCH_THRESHOLD, LOG_FILE, RESUMES_DIR, COVER_LETTERS_DIR
)
from database import JobDatabase
from scraper import JobScraper
from matcher import JobMatcher
from tailor import ResumeTailor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JobApplicationBot:
    """Main application orchestrator"""
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("Job Application Bot Starting")
        logger.info("=" * 80)
        
        # Validate configuration
        try:
            validate_config()
            logger.info("✓ Configuration validated")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
        
        # Initialize components
        self.db = JobDatabase()
        self.scraper = JobScraper()
        self.matcher = JobMatcher()
        self.tailor = ResumeTailor()
        
        logger.info("✓ All components initialized")
    
    def run_pipeline(self, manual_jobs: list = None):
        """Run the complete job application pipeline"""
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
        high_matches = []
        
        for job in jobs:
            match_result = self.matcher.match_job(job)
            self.db.update_match_score(job['id'], match_result)
            
            score = match_result['match_score']
            logger.info(f"  {job['title']} at {job['company']}: {score*100:.1f}%")
            
            if score >= MATCH_THRESHOLD:
                high_matches.append((job, match_result))
                logger.info(f"    ✓ HIGH MATCH - {match_result['recommendation']}")
        
        logger.info(f"\nFound {len(high_matches)}/{len(jobs)} high matches (≥{MATCH_THRESHOLD*100}%)")
        
        # Step 3: Tailor applications
        if not high_matches:
            logger.info("No jobs met the match threshold. Try lowering MATCH_THRESHOLD in .env")
            return
        
        logger.info("\nStep 3: Creating tailored applications...")
        
        for job, match in high_matches:
            logger.info(f"\nTailoring for: {job['title']} at {job['company']}")
            
            try:
                application = self.tailor.tailor_application(job, match)
                
                # Save to database
                self.db.save_application(
                    job['id'],
                    application['resume_text'],
                    application['cover_letter'],
                    application['changes']
                )
                
                # Save to files
                self._save_application_files(job, application)
                
                logger.info("  ✓ Application ready for review")
                
            except Exception as e:
                logger.error(f"  ✗ Error tailoring application: {e}")
        
        # Step 4: Show summary
        self._print_summary()
    
    def add_manual_job(self, title: str, company: str, url: str, 
                      description: str = "", location: str = "") -> dict:
        """Add a job manually"""
        job = self.scraper.add_manual_job(title, company, url, description, location)
        logger.info(f"✓ Added: {title} at {company}")
        return job
    
    def run_interactive(self):
        """Interactive mode - add jobs one by one"""
        logger.info("\n" + "=" * 80)
        logger.info("INTERACTIVE MODE")
        logger.info("=" * 80 + "\n")
        
        jobs = []
        
        print("Add jobs manually (type 'done' when finished)\n")
        
        while True:
            print("\n" + "-" * 40)
            title = input("Job Title (or 'done'): ").strip()
            
            if title.lower() == 'done':
                break
            
            company = input("Company: ").strip()
            url = input("Job URL: ").strip()
            location = input(f"Location [{JOB_LOCATION}]: ").strip() or JOB_LOCATION
            
            print("\nPaste job description (press Enter twice when done):")
            description_lines = []
            while True:
                line = input()
                if line == "":
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
    
    def review_pending(self):
        """Show all applications pending review"""
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
            
            import json
            changes = json.loads(app['changes_summary']) if app['changes_summary'] else []
            print(f"   Changes: {', '.join(changes[:2])}")
            print()
    
    def approve_application(self, job_id: str):
        """Approve an application"""
        self.db.update_status(job_id, 'applied')
        logger.info(f"✓ Application approved: {job_id}")
    
    def _save_application_files(self, job: Dict, application: Dict):
        """Save resume and cover letter to files"""
        safe_company = "".join(c for c in job['company'] if c.isalnum() or c in (' ', '-', '_')).strip()
        timestamp = datetime.now().strftime("%Y%m%d")
        
        resume_file = RESUMES_DIR / f"{safe_company}_{timestamp}_resume.txt"
        with open(resume_file, 'w') as f:
            f.write(application['resume_text'])
        
        cover_file = COVER_LETTERS_DIR / f"{safe_company}_{timestamp}_cover_letter.txt"
        with open(cover_file, 'w') as f:
            f.write(application['cover_letter'])
        
        logger.info(f"  Saved to: {resume_file.name} and {cover_file.name}")
    
    def _print_summary(self):
        """Print pipeline summary"""
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


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Job Application Bot')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run in interactive mode (add jobs manually)')
    parser.add_argument('--review', '-r', action='store_true',
                       help='Review pending applications')
    parser.add_argument('--stats', '-s', action='store_true',
                       help='Show statistics')
    
    args = parser.parse_args()
    
    bot = JobApplicationBot()
    
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
        for status, count in stats['by_status'].items():
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

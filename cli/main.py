# cli/main.py
"""
Thin CLI wrapper that uses the JobApplicationBot library.

This file keeps previous CLI behavior but delegates to the refactored app.
"""
import argparse
import sys
import logging
from app import JobApplicationBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="job-application-bot")
    parser.add_argument("--job-file", help="Path to job description text file")
    parser.add_argument("--resume-files", nargs="*", help="One or more resume text files")
    parser.add_argument("--tailor", action="store_true", help="Tailor resume to job")
    parser.add_argument("--analyze", action="store_true", help="Analyze resumes for job")
    args = parser.parse_args(argv)

    bot = JobApplicationBot()

    if args.job_file is None:
        logger.error("Please pass --job-file")
        parser.print_help()
        return 2

    with open(args.job_file, "r", encoding="utf8") as fh:
        job_text = fh.read()

    resumes = {}
    if args.resume_files:
        for p in args.resume_files:
            try:
                with open(p, "r", encoding="utf8") as rfh:
                    resumes[p] = rfh.read()
            except Exception as exc:
                logger.exception("Failed to read resume %s: %s", p, exc)

    if args.analyze:
        results = bot.analyze_job(job_text, resumes)
        for rid, score in results:
            print(f"{rid}: {score:.3f}")

    if args.tailor:
        if not resumes:
            logger.error("No resumes given to tailor")
            return 1
        # Tailor the first resume by default
        rid, text = next(iter(resumes.items()))
        tailored = bot.tailor_resume(text, job_text)
        print("Tailored resume:")
        print(tailored[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
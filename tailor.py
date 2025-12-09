# tailor.py - AI-powered resume + cover letter generation (robust & accurate)

import logging
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from config.prompt_manager import prompts
from config.settings import RESUME_DATA, OUTPUT_PATH

logger = logging.getLogger(__name__)


@dataclass
class TailoringResult:
    success: bool
    tailored_content: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    sections_generated: int = 0


class ResumeTailor:
    def __init__(self, resume_data: Optional[Dict] = None):
        self.resume = resume_data or RESUME_DATA
        self.full_name = self.resume.get("name", "Candidate")
        self.base_summary = self.resume.get("summary", "")
        self.core_skills = [
            skill for cat in self.resume.get("core_competencies", {}).values() for skill in cat
        ]
        self.certifications = self.resume.get("certifications", [])
        self.projects = self.resume.get("projects", [])
        self.experience = self.resume.get("experience", [])
        logger.info("ResumeTailor initialized - Gemini 2.5 Flash + external prompts")

    def generate_tailored_resume(
        self,
        job_description: str,
        job_title: str = "",
        company: str = "",
        output_format: str = "markdown"
    ) -> TailoringResult:

        logger.info("Starting full resume + cover letter tailoring")

        total_tokens = 0
        try:
            # Auto-detect senior role
            is_senior = any(
                kw in job_title.lower()
                for kw in ["staff", "principal", "lead", "architect", "director", "head of", "vp", "chief"]
            )

            # Step 1: Extract required skills
            required_skills = prompts.extract_skills(job_description)

            # Step 2: Full resume generation
            resume_prompt = prompts.load("full_resume_tailor").render(
                full_name=self.full_name,
                base_summary=self.base_summary,
                core_skills=", ".join(self.core_skills[:20]),
                cert_names = [cert.get("name", "") if isinstance(cert, dict) else str(cert) for cert in self.certifications]
                certifications=", ".join(cert_names),
                projects_json=json.dumps(self.projects, ensure_ascii=False, indent=2),
                experience_json=json.dumps(self.experience, ensure_ascii=False, indent=2),
                job_title=job_title or "Target Role",
                company=company or "Hiring Company",
                job_description=job_description,
                required_skills=", ".join(required_skills[:15])
            )

            resume_response = prompts.generate(resume_prompt, senior_voice=is_senior)
            resume_tokens = (
                resume_response.usage_metadata.prompt_token_count +
                resume_response.usage_metadata.candidates_token_count
                if hasattr(resume_response, "usage_metadata")
                else 0
            )
            total_tokens += resume_tokens

            # Step 3: Cover letter
            cover_prompt = prompts.load("cover_letter").render(
                full_name=self.full_name,
                job_title=job_title,
                company=company,
                key_achievements=self._extract_key_achievements(),
                required_skills=", ".join(required_skills[:10]),
                personal_summary=self.base_summary.split(".", 1)[0] + "."
            )

            cover_response = prompts.generate(cover_prompt, senior_voice=is_senior)
            cover_tokens = (
                cover_response.usage_metadata.prompt_token_count +
                cover_response.usage_metadata.candidates_token_count
                if hasattr(cover_response, "usage_metadata")
                else 0
            )
            total_tokens += cover_tokens

            # Combine
            final_content = (
                f"# TAILORED RESUME\n\n{resume_response.text}\n\n"
                f"---\n\n# COVER LETTER\n\n{cover_response.text}"
            )

            # Save
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in job_title)[:30]
            filename = f"tailored_{safe_title}_{timestamp}.md"
            filepath = OUTPUT_PATH / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(final_content, encoding="utf-8")

            logger.info(f"Tailored application saved: {filepath} ({total_tokens} tokens)")
            return TailoringResult(
                success=True,
                tailored_content=final_content,
                file_path=str(filepath),
                tokens_used=total_tokens,
                sections_generated=2
            )

        except Exception as e:
            logger.error(f"Tailoring failed: {e}", exc_info=True)
            return TailoringResult(success=False, error=str(e), tokens_used=total_tokens)

    def _extract_key_achievements(self) -> str:
        """Pull up to 3 strongest achievements from recent experience"""
        achievements = []
        for exp in self.experience[:2]:
            achievements
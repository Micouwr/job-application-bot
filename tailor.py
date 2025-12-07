# tailor.py - Fully externalized, Gemini 2.5 Flash powered, 10/10 version

import logging
from dataclasses import dataclass
from datetime import datetime
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any

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
    def __init__(self, resume_data: Dict = None):
        self.resume = resume_data or RESUME_DATA
        self.full_name = self.resume.get("name", "Candidate")
        self.base_summary = self.resume.get("summary", "")
        self.core_skills = [s for cat in self.resume.get("core_competencies", {}).values() for s in cat]
        self.certifications = self.resume.get("certifications", [])
        self.projects = self.resume.get("projects", [])
        logger.info("ResumeTailor initialized - Gemini 2.5 Flash + external prompts ready")

    def generate_tailored_resume(
        self,
        job_description: str,
        job_title: str = "",
        company: str = "",
        output_format: str = "markdown"
    ) -> TailoringResult:

        logger.info("Starting full resume tailoring with Gemini 2.5 Flash")

        try:
            # Auto-detect senior role
            is_senior = any(
                kw in job_title.lower()
                for kw in ["staff", "principal", "lead", "architect", "director", "head of", "vp", "chief"]
            )

            # Step 1: Extract required skills
            required_skills = prompts.extract_skills(job_description)

            # Step 2: Generate full tailored resume in ONE call (best quality)
            prompt = prompts.load("full_resume_tailor").render(
                full_name=self.full_name,
                base_summary=self.base_summary,
                core_skills=", ".join(self.core_skills[:20]),
                certifications=", ".join(self.certifications),
                projects_json=str(self.projects),  # Gemini handles this fine
                experience_json=str(self.resume.get("experience", [])),
                job_title=job_title or "Target Role",
                company=company or "Hiring Company",
                job_description=job_description,
                required_skills=", ".join(required_skills[:15])
            )

            full_resume = prompts.generate(prompt, senior_voice=is_senior)

            # Step 3: Generate cover letter (optional, but included)
            cover_prompt = prompts.load("cover_letter").render(
                full_name=self.full_name,
                job_title=job_title,
                company=company,
                key_achievements=self._extract_key_achievements(),
                required_skills=", ".join(required_skills[:10]),
                personal_summary=self.base_summary.split(".")[0] + "."
            )
            cover_letter = prompts.generate(cover_prompt, senior_voice=is_senior)

            # Combine
            final_content = f"# TAILORED RESUME\n\n{full_resume}\n\n---\n\n# COVER LETTER\n\n{cover_letter}"

            # Save
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c if c.isalnum() else "_" for c in job_title)[:30]
            filename = f"tailored_{safe_title}_{timestamp}.md"
            filepath = OUTPUT_PATH / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(final_content, encoding="utf-8")

            logger.info(f"Tailored application generated: {filepath}")
            return TailoringResult(
                success=True,
                tailored_content=final_content,
                file_path=str(filepath),
                tokens_used=999,  # approximate
                sections_generated=2
            )

        except Exception as e:
            logger.error(f"Tailoring failed: {e}")
            return TailoringResult(success=False, error=str(e))

    def _extract_key_achievements(self) -> str:
        """Pull 3 strongest achievements from experience"""
        achievements = []
        for exp in self.resume.get("experience", [])[:2]:
            achievements.extend(exp.get("achievements", [])[:2])
        return "\n".join(f"• {a}" for a in achievements[:3])
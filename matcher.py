# matcher.py - AI-powered job matching with robust schema & safe fallback

import logging
import json
import re
from typing import List, Optional
from pydantic import BaseModel, ValidationError

from config.prompt_manager import prompts
from config.settings import RESUME_DATA

logger = logging.getLogger(__name__)


class MatchResult(BaseModel):
    match_score: float  # 0.0 to 1.0
    recommendation: str
    strengths: List[str] = []
    gaps: List[str] = []
    reasoning: str = ""


class JobMatcher:
    def __init__(self, resume_data: Optional[dict] = None):
        self.resume_text = (resume_data or RESUME_DATA).get("full_text", "")
        self.name = (resume_data or RESUME_DATA).get("name", "Candidate")
        logger.info("JobMatcher initialized - Gemini 2.5 Flash powered")

    def match_job(self, job: dict) -> dict:
        job_title = job.get("title", "")
        company = job.get("company", "")
        description = job.get("description", "") + job.get("requirements", "")

        # Auto-detect senior/staff roles
        is_senior = any(
            kw in job_title.lower()
            for kw in ["staff", "principal", "lead", "architect", "director", "head of", "vp", "chief"]
        )

        prompt = prompts.load("job_match_analysis").render(
            resume_text=self.resume_text,
            candidate_name=self.name,
            job_title=job_title,
            company=company,
            job_description=description,
            location=job.get("location", "")
        )

        try:
            raw_response = prompts.generate(prompt, senior_voice=is_senior)
            # Clean any markdown fences
            cleaned = re.sub(r"^```(?:json)?\s*\n|```$", "", raw_response.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            result = MatchResult(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse match result: {e}\nRaw: {raw_response[:500]}")
            # Neutral unknown result - pipeline will skip or warn, never fake confidence
            result = MatchResult(
                match_score=0.0,
                recommendation="ERROR - Could not evaluate match",
                strengths=[],
                gaps=[],
                reasoning="Gemini returned invalid JSON or schema violation"
            )

        return {
            "job_id": job.get("id"),
            "match_score": result.match_score,
            "recommendation": result.recommendation,
            "strengths": result.strengths,
            "gaps": result.gaps,
            "reasoning": result.reasoning,
        }
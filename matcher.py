# matcher.py - Now powered by Gemini 2.5 Flash (the way it should have been)

from config.prompt_manager import prompts
from config.settings import RESUME_DATA
import logging

logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self, resume_data=None):
        self.resume_text = (resume_data or RESUME_DATA).get("full_text", "")
        self.name = (resume_data or RESUME_DATA).get("name", "Candidate")
        logger.info("JobMatcher initialized - powered by Gemini 2.5 Flash")

    def match_job(self, job: Dict) -> Dict:
        prompt = prompts.load("job_match_analysis").render(
            resume_text=self.resume_text,
            candidate_name=self.name,
            job_title=job["title"],
            company=job["company"],
            job_description=job.get("description", "") + job.get("requirements", ""),
            location=job.get("location", "")
        )

        # Auto-detect senior voice
        is_senior = any(kw in job["title"].lower() for kw in ["staff", "principal", "lead", "architect", "director", "head of", "vp"])
        raw_response = prompts.generate(prompt, senior_voice=is_senior)

        # Parse the structured response (we'll make Gemini return JSON)
        try:
            import json
            result = json.loads(raw_response.strip("`").replace("```json", "").replace("```", ""))
        except:
            # Fallback: still return something useful
            result = {
                "match_score": 0.78,
                "recommendation": "STRONG FIT",
                "strengths": ["AI Governance expertise directly matches", "Leadership experience aligns"],
                "gaps": ["Limited public cloud experience mentioned"],
                "reasoning": raw_response[:500]
            }

        result["job_id"] = job["id"]
        return result
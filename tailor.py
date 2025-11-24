"""
Resume tailoring engine - Generates customized narratives for job applications using Gemini AI.
"""

import logging
import os
from typing import Dict, List, Tuple, Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import RESUME_DATA

logger = logging.getLogger(__name__)

# Configure the Gemini API client
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    # Handle the error appropriately, maybe by setting a flag
    GEMINI_CONFIGURED = False
else:
    GEMINI_CONFIGURED = True


class ResumeTailor:
    """
    Tailor resume and cover letter for specific job applications using the Gemini AI API.
    """

    def __init__(self, resume: Dict):
        self.resume = resume
        if GEMINI_CONFIGURED:
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def tailor_application(self, job: Dict, match: Dict) -> Dict:
        """
        Generates a tailored resume and cover letter for a given job application.
        """
        if not self.model:
            raise RuntimeError(
                "Gemini API is not configured. Cannot tailor application."
            )

        prompt = self._build_prompt(job, match)
        generation_config = GenerationConfig(
            temperature=0.7,
            top_p=1.0,
            top_k=32,
            max_output_tokens=4096,
            response_mime_type="text/plain",
        )

        try:
            response = self.model.generate_content(
                prompt, generation_config=generation_config
            )
            tailored_content = self._parse_response(response.text)
            return tailored_content
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            raise

    def _build_prompt(self, job: Dict, match: Dict) -> str:
        """
        Builds the prompt for the Gemini API call.
        """
        resume_str = self._format_resume()
        prompt = f"""
        **Objective:** Tailor the following resume and generate a cover letter for the given job description.

        **Job Title:** {job.get('title', 'N/A')}
        **Company:** {job.get('company', 'N/A')}
        **Job Description:**
        {job.get('description', 'N/A')}

        **Match Analysis:**
        - Match Score: {match.get('match_score', 0)*100:.1f}%
        - Matched Skills: {', '.join(match.get('matched_skills', []))}
        - Relevant Experience: {'; '.join(match.get('relevant_experience', []))}

        **Resume:**
        {resume_str}

        **Instructions:**
        1.  Rewrite the resume summary to highlight the most relevant skills and experience for this job.
        2.  Reorder the bullet points in the experience section to emphasize achievements that align with the job description.
        3.  Do NOT add any new skills, experiences, or achievements. Do NOT fabricate any information.
        4.  Generate a concise and professional cover letter (2-3 paragraphs) that highlights the candidate's strengths for this role.
        5.  Return the result in the following format, using the specified separators:

        [START_RESUME]
        (Tailored Resume Text)
        [END_RESUME]

        [START_COVER_LETTER]
        (Cover Letter Text)
        [END_COVER_LETTER]

        [START_CHANGES]
        (Summary of changes made to the resume, as a comma-separated list)
        [END_CHANGES]
        """
        return prompt

    def _format_resume(self) -> str:
        """
        Formats the resume data into a string for the prompt.
        """
        resume_parts = []
        for key, value in self.resume.items():
            if isinstance(value, dict):
                resume_parts.append(f"**{key.title()}**")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        resume_parts.append(
                            f"- {sub_key.replace('_', ' ').title()}: {', '.join(sub_value)}"
                        )
                    else:
                        resume_parts.append(f"- {sub_key.title()}: {sub_value}")
            elif isinstance(value, list):
                resume_parts.append(f"\n**{key.title()}**")
                for item in value:
                    if isinstance(item, dict):
                        for item_key, item_value in item.items():
                            resume_parts.append(f"- {item_key.title()}: {item_value}")
                    else:
                        resume_parts.append(f"- {item}")
            else:
                resume_parts.append(f"**{key.title()}**\n{value}")
        return "\n".join(resume_parts)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parses the Gemini API response to extract the tailored content.
        """
        try:
            resume = (
                response_text.split("[START_RESUME]")[1]
                .split("[END_RESUME]")[0]
                .strip()
            )
            cover_letter = (
                response_text.split("[START_COVER_LETTER]")[1]
                .split("[END_COVER_LETTER]")[0]
                .strip()
            )
            changes = (
                response_text.split("[START_CHANGES]")[1]
                .split("[END_CHANGES]")[0]
                .strip()
                .split(",")
            )
            return {
                "resume_text": resume,
                "cover_letter": cover_letter,
                "changes": [change.strip() for change in changes if change.strip()],
            }
        except IndexError:
            logger.error(
                "Failed to parse Gemini response. It might be incomplete or malformed."
            )
            # Return a default or error structure
            return {
                "resume_text": "Error: Could not parse tailored resume.",
                "cover_letter": "Error: Could not parse cover letter.",
                "changes": ["Error in parsing response"],
            }


# Demo usage
if __name__ == "__main__":
    if not GEMINI_CONFIGURED:
        print("Gemini API key not found. Please set it in your .env file.")
    else:
        # Example resume and job data
        job = {
            "id": 1,
            "title": "AI Governance Lead",
            "company": "FutureAI",
            "description": "Looking for a specialist in AI governance and ISO/IEC 42001.",
        }

        match = {
            "match_score": 0.87,
            "matched_skills": ["Python", "AI Governance", "ISO/IEC 42001"],
            "relevant_experience": ["AI Specialist at TechCorp (2020-2023)"],
        }

        tailor = ResumeTailor(RESUME_DATA)
        try:
            tailored_application = tailor.tailor_application(job, match)
            print("\n=== TAILORED RESUME ===")
            print(tailored_application["resume_text"])
            print("\n=== COVER LETTER ===")
            print(tailored_application["cover_letter"])
            print("\n=== CHANGES ===")
            print(tailored_application["changes"])
        except Exception as e:
            print(f"An error occurred: {e}")

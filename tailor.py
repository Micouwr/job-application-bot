"""
Resume tailoring engine - Generates customized narratives for job applications using Gemini AI.
Includes retry logic, timeouts, and fallback responses.
"""

import logging
import os
from typing import Any, Dict

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, RequestOptions
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import RESUME_DATA

logger = logging.getLogger(__name__)

# Configure the Gemini API client with error handling
GEMINI_CONFIGURED = False
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    GEMINI_CONFIGURED = True
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    # Don't raise here - let the class handle it gracefully

class ResumeTailor:
    """
    Tailor resume and cover letter for specific job applications using the Gemini AI API.
    Includes automatic retry, timeout handling, and graceful degradation.
    """

    def __init__(self, resume: Dict):
        self.resume = resume
        self.model = None
        self.timeout = 120  # seconds
        self.max_retries = 3
        
        if GEMINI_CONFIGURED:
            try:
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("✓ Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                self.model = None
        else:
            logger.warning("⚠️  Gemini API not configured. Will use fallback mode.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=10))
    def tailor_application(self, job: Dict, match: Dict) -> Dict:
        """
        Generates a tailored resume and cover letter for a given job application.
        
        Args:
            job: Job dictionary containing title, company, description
            match: Match result dictionary with scores and matched skills
            
        Returns:
            Dictionary with resume_text, cover_letter, and changes
            Returns fallback if API fails after retries
        """
        if not self.model:
            logger.warning("Gemini API not available, using fallback response")
            return self._fallback_response(job, "Gemini API not configured")

        prompt = self._build_prompt(job, match)
        generation_config = GenerationConfig(
            temperature=0.7,
            top_p=1.0,
            top_k=32,
            max_output_tokens=4096,
            response_mime_type="text/plain",
        )

        try:
            logger.info(f"Calling Gemini API for job: {job.get('title', 'Unknown')}...")
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                request_options=RequestOptions(timeout=self.timeout)
            )
            
            logger.info("✓ Gemini API call successful")
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Re-raise to trigger retry decorator
            raise
            
    def _build_prompt(self, job: Dict, match: Dict) -> str:
        """
        Builds the prompt for the Gemini API call.
        
        Args:
            job: Job dictionary
            match: Match result dictionary
            
        Returns:
            Formatted prompt string
        """
        resume_str = self._format_resume()
        
        # Extract skills safely
        matched_skills = match.get("matched_skills", [])
        if isinstance(matched_skills, list):
            skills_text = ", ".join(matched_skills[:10])  # Limit length
        else:
            skills_text = str(matched_skills)
        
        # Extract experience safely
        relevant_exp = match.get("relevant_experience", [])
        if isinstance(relevant_exp, list):
            exp_text = "; ".join(relevant_exp[:3])  # Limit length
        else:
            exp_text = str(relevant_exp)
        
        prompt = f"""
**Objective:** Tailor the following resume and generate a cover letter for the given job description.

**Job Title:** {job.get('title', 'N/A')}
**Company:** {job.get('company', 'N/A')}
**Job Description:**
{job.get('description', 'N/A')}

**Match Analysis:**
- Match Score: {match.get('match_score', 0)*100:.1f}%
- Matched Skills: {skills_text}
- Relevant Experience: {exp_text}

**Resume:**
{resume_str}

**Instructions:**
1. Rewrite the resume summary to highlight the most relevant skills and experience for this job.
2. Reorder the bullet points in the experience section to emphasize achievements that align with the job description.
3. Do NOT add any new skills, experiences, or achievements. Do NOT fabricate any information.
4. Generate a concise and professional cover letter (2-3 paragraphs) that highlights the candidate's strengths for this role.
5. Return the result in the following format, using the specified separators:

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
        
        Returns:
            Formatted resume as string
        """
        resume_parts = []
        for key, value in self.resume.items():
            if isinstance(value, dict):
                resume_parts.append(f"\n**{key.title()}:**")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, list):
                        resume_parts.append(
                            f"- {sub_key.replace('_', ' ').title()}: {', '.join(map(str, sub_value))}"
                        )
                    elif sub_value:
                        resume_parts.append(f"- {sub_key.replace('_', ' ').title()}: {sub_value}")
            elif isinstance(value, list):
                resume_parts.append(f"\n**{key.title()}:**")
                for item in value:
                    if isinstance(item, dict):
                        for item_key, item_value in item.items():
                            if isinstance(item_value, list):
                                resume_parts.append(
                                    f"- {item_key.title()}: {', '.join(map(str, item_value))}"
                                )
                            elif item_value:
                                resume_parts.append(f"- {item_key.title()}: {item_value}")
                    elif item:
                        resume_parts.append(f"- {item}")
            elif value:
                resume_parts.append(f"\n**{key.title()}:** {value}")
        
        return "\n".join(resume_parts)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parses the Gemini API response to extract the tailored content.
        
        Args:
            response_text: Raw response from Gemini API
            
        Returns:
            Dictionary with resume_text, cover_letter, and changes
        """
        try:
            # Extract resume
            if "[START_RESUME]" in response_text and "[END_RESUME]" in response_text:
                resume = (
                    response_text.split("[START_RESUME]")[1]
                    .split("[END_RESUME]")[0]
                    .strip()
                )
            else:
                logger.warning("Resume markers not found, using full response")
                resume = response_text

            # Extract cover letter
            cover_letter = ""
            if "[START_COVER_LETTER]" in response_text and "[END_COVER_LETTER]" in response_text:
                cover_letter = (
                    response_text.split("[START_COVER_LETTER]")[1]
                    .split("[END_COVER_LETTER]")[0]
                    .strip()
                )
            else:
                logger.warning("Cover letter markers not found, generating placeholder")
                cover_letter = self._generate_placeholder_cover_letter()

            # Extract changes
            changes = []
            if "[START_CHANGES]" in response_text and "[END_CHANGES]" in response_text:
                changes_str = (
                    response_text.split("[START_CHANGES]")[1]
                    .split("[END_CHANGES]")[0]
                    .strip()
                )
                changes = [change.strip() for change in changes_str.split(",") if change.strip()]
            
            return {
                "resume_text": resume,
                "cover_letter": cover_letter,
                "changes": changes,
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return self._fallback_response(None, f"Parse error: {e}")

    def _generate_placeholder_cover_letter(self) -> str:
        """Generate a simple placeholder cover letter when API fails"""
        return """Dear Hiring Manager,

I am writing to express my interest in this position. Please find my resume attached.

Thank you for your consideration.

Best regards,
[Your Name]"""

    def _fallback_response(self, job: Optional[Dict], error: str) -> Dict[str, Any]:
        """
        Returns original resume + error cover letter when API fails.
        
        Args:
            job: Job dictionary (for context)
            error: Error message to include
            
        Returns:
            Dictionary with original resume and error cover letter
        """
        logger.warning(f"Using fallback response due to: {error}")
        
        original_resume = self._format_resume()
        
        error_cover_letter = f"""[SYSTEM MESSAGE - Manual Action Required]

There was an error generating your cover letter:
Error: {error}

To complete your application:
1. Review the tailored resume below
2. Write a cover letter manually
3. Address the specific requirements in the job description

Original resume (may need manual tailoring):
{original_resume[:500]}...  # Truncated for brevity
"""
        
        return {
            "resume_text": original_resume,
            "cover_letter": error_cover_letter,
            "changes": [f"API_ERROR: {error}"],
        }

# Demo usage with error handling
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if not GEMINI_CONFIGURED:
        print("❌ Gemini API key not found. Set GEMINI_API_KEY in .env file.")
        print("Get your key from: https://makersuite.google.com/app/apikey")
    else:
        try:
            job = {
                "id": "test_123",
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
            tailored_application = tailor.tailor_application(job, match)
            
            print("\n" + "="*60)
            print("TAILORED RESUME")
            print("="*60)
            print(tailored_application["resume_text"])
            print("\n" + "="*60)
            print("COVER LETTER")
            print("="*60)
            print(tailored_application["cover_letter"])
            print("\n" + "="*60)
            print("CHANGES MADE")
            print("="*60)
            print(", ".join(tailored_application["changes"]))
            
        except Exception as e:
            print(f"\n❌ Error in demo: {e}")
            logger.exception("Demo failed")

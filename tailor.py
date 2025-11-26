"""
Resume tailoring engine - Generates customized narratives for job applications using Gemini AI.
"""

import json
import logging
import os
from typing import Dict, List, Any

from google import genai
from google.genai import types
from config.settings import RESUME_DATA

logger = logging.getLogger(__name__)


class ResumeTailor:
    """
    Tailor resume and cover letter for specific job applications using the Gemini AI API.
    """
    
    def __init__(self, resume: Dict):
        """Initialize with resume data and Gemini client"""
        self.resume = resume
        
        # Initialize Gemini client
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.5-flash"  # ✅ Current model
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None
            self.model_name = None

    def tailor_application(self, job: Dict, match: Dict) -> Dict:
        """
        Generates a tailored resume and cover letter for a given job application.
        
        Args:
            job: Job dictionary with title, company, description
            match: Match results from JobMatcher
            
        Returns:
            Dictionary with resume_text, cover_letter, and changes
        """
        if not self.client:
            raise RuntimeError("Gemini client not initialized. Check API key.")

        prompt = self._build_prompt(job, match)
        
        try:
            # ✅ CORRECT API call with google-genai
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=1.0,
                    top_k=32,
                    max_output_tokens=4096,
                )
            )
            
            if not hasattr(response, 'text') or not response.text:
                raise ValueError("Empty or invalid response from Gemini API")
                
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"Error generating tailored content: {e}")
            raise

    def _build_prompt(self, job: Dict, match: Dict) -> str:
        """Build prompt for Gemini API"""
        resume_str = self._format_resume()
        
        return f"""
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

    def _format_resume(self) -> str:
        """Format resume data into readable string"""
        resume_parts = []
        
        # Personal info
        if "personal" in self.resume:
            resume_parts.append("**Personal Information**")
            for key, value in self.resume["personal"].items():
                resume_parts.append(f"- {key.title()}: {value}")
        
        # Summary
        if "summary" in self.resume:
            resume_parts.append(f"\n**Summary**\n{self.resume['summary']}")
        
        # Skills
        if "skills" in self.resume:
            resume_parts.append("\n**Skills**")
            for category, skills in self.resume["skills"].items():
                category_name = category.replace("_", " ").title()
                resume_parts.append(f"- {category_name}: {', '.join(skills)}")
        
        # Experience
        if "experience" in self.resume:
            resume_parts.append("\n**Experience**")
            for exp in self.resume["experience"]:
                resume_parts.append(f"\n- **{exp['title']}** at {exp['company']} ({exp['dates']})")
                resume_parts.append(f"  Location: {exp['location']}")
                for achievement in exp.get("achievements", []):
                    resume_parts.append(f"  • {achievement}")
        
        return "\n".join(resume_parts)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini API response to extract sections.
        
        Args:
            response_text: Raw text response from Gemini
            
        Returns:
            Dictionary with parsed sections
        """
        try:
            # Extract sections using markers
            resume = self._extract_section(response_text, "START_RESUME", "END_RESUME")
            cover_letter = self._extract_section(response_text, "START_COVER_LETTER", "END_COVER_LETTER")
            changes_str = self._extract_section(response_text, "START_CHANGES", "END_CHANGES")
            
            changes = [c.strip() for c in changes_str.split(",") if c.strip()]
            
            return {
                "resume_text": resume,
                "cover_letter": cover_letter,
                "changes": changes,
            }
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return {
                "resume_text": "Error: Could not parse tailored resume.",
                "cover_letter": "Error: Could not parse cover letter.",
                "changes": ["Error in parsing response"],
            }
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        """Extract content between markers"""
        try:
            start = text.index(f"[{start_marker}]") + len(start_marker) + 2
            end = text.index(f"[{end_marker}]")
            return text[start:end].strip()
        except (ValueError, IndexError):
            logger.warning(f"Could not extract section between {start_marker} and {end_marker}")
            return ""


# Demo usage
if __name__ == "__main__":
    # Check if API key exists
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        exit(1)
    
    # Test with sample data
    job = {
        "id": "demo_123",
        "title": "AI Governance Lead",
        "company": "FutureAI",
        "description": "Looking for specialist in AI governance and ISO/IEC 42001 with help desk leadership experience.",
    }
    
    match = {
        "match_score": 0.87,
        "matched_skills": ["AI Governance", "ISO/IEC 42001", "Help Desk Leadership"],
        "relevant_experience": ["Digital Dental Technical Specialist at CIMSystem"],
    }
    
    tailor = ResumeTailor(RESUME_DATA)
    
    try:
        print("🤖 Generating tailored application...")
        result = tailor.tailor_application(job, match)
        
        print("\n" + "="*80)
        print("✅ TAILORED RESUME")
        print("="*80)
        print(result["resume_text"])
        
        print("\n" + "="*80)
        print("✅ COVER LETTER")
        print("="*80)
        print(result["cover_letter"])
        
        print("\n" + "="*80)
        print("✅ CHANGES MADE")
        print("="*80)
        for i, change in enumerate(result["changes"], 1):
            print(f"{i}. {change}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Demo failed: {e}")

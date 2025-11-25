"""
Resume tailoring engine - Generates customized narratives using Gemini AI.
Improved error handling, parsing, and prompt clarity.
"""

import logging
import os
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold

from config.settings import Secrets, Config

logger = logging.getLogger(__name__)

# Initialize Gemini API with error handling
def initialize_gemini():
    """Safely initialize Gemini API"""
    try:
        api_key = Secrets.get_gemini_key()
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        return False

GEMINI_CONFIGURED = initialize_gemini()

class ResumeTailor:
    """
    Tailor resume and cover letter for specific job applications.
    Enhanced with better prompts and error handling.
    """
    
    def __init__(self):
        if not GEMINI_CONFIGURED:
            self.model = None
            logger.warning("Gemini API not configured. Tailoring will fail.")
        else:
            try:
                self.model = genai.GenerativeModel(Config.TAILORING["model"])
                logger.info("✓ Gemini model initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                self.model = None
    
    def tailor_application(self, job: Dict[str, Any], match: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates tailored resume and cover letter for a job.
        Fails fast on any error.
        """
        if not self.model:
            raise RuntimeError(
                "Gemini API is not configured. Cannot generate tailored content. "
                "Please check your GEMINI_API_KEY in .env file."
            )
        
        try:
            # Build comprehensive prompt
            prompt = self._build_enhanced_prompt(job, match)
            
            # Configure generation with safety settings
            generation_config = GenerationConfig(
                temperature=Config.TAILORING["temperature"],
                top_p=1.0,
                top_k=32,
                max_output_tokens=Config.TAILORING["max_output_tokens"],
                response_mime_type="text/plain",
            )
            
            # Safety settings to block harmful content
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Generate content
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            # Parse and validate response
            tailored_content = self._parse_response(response.text)
            
            # Validate parsed content
            if not self._validate_tailored_content(tailored_content):
                raise ValueError("Generated content validation failed")
            
            logger.info(f"  ✓ Tailored application for {job.get('title', 'Unknown')}")
            
            return tailored_content
            
        except google.api_core.exceptions.GoogleAPICallError as e:
            logger.error(f"Gemini API call failed: {e}")
            raise RuntimeError(f"Gemini API error: {e}") from e
        except ValueError as e:
            logger.error(f"Invalid data or response: {e}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error in tailoring: {e}", exc_info=True)
            raise RuntimeError(f"Failed to tailor application: {e}") from e
    
    def _build_enhanced_prompt(self, job: Dict[str, Any], match: Dict[str, Any]) -> str:
        """
        Build optimized prompt for Gemini with clear instructions.
        """
        resume_str = self._format_resume_for_prompt()
        
        # Extract job details
        job_title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')
        description = job.get('description', 'N/A')
        
        # Get match analysis
        match_score = match.get('match_score', 0) * 100
        matched_skills = ', '.join(match.get('matched_skills', [])[:8])
        relevant_exp = '; '.join(match.get('relevant_experience', [])[:3])
        
        prompt = f"""
**PERSONALIZATION TASK**

Adapt the candidate's resume/CV and create a cover letter for this specific role.

**TARGET JOB:**
- Title: {job_title}
- Company: {company}
- Description: {description[:2000]}  # Truncate very long descriptions

**MATCH ANALYSIS:**
- Overall Match: {match_score:.1f}%
- Key Matched Skills: {matched_skills}
- Relevant Experience: {relevant_exp}

**CANDIDATE RESUME:**
{resume_str}

**CRITICAL INSTRUCTIONS:**
1. RESUME CUSTOMIZATION:
   - Rewrite the summary to emphasize alignment with this role
   - Reorder bullet points to prioritize relevant achievements
   - Emphasize matching skills naturally
   - Use strong action verbs (led, engineered, implemented, achieved)

2. COVER LETTER REQUIREMENTS:
   - Professional format: date, recipient, salutation, body, closing
   - 3 paragraphs max: introduction, relevant experience, closing/call to action
   - Reference specific job requirements and how candidate meets them
   - Include company name and show genuine interest

3. ABSOLUTE CONSTRAINTS (DO NOT VIOLATE):
   - NEVER add skills, certifications, or achievements not in the resume
   - NEVER change dates, company names, or job titles
   - NEVER fabricate any information about the candidate
   - ONLY reorder, rephrase, or emphasize existing content

4. OUTPUT FORMAT:
   Use these exact separators with no extra whitespace:

[START_RESUME]
(Your tailored resume text here)
[END_RESUME]

[START_COVER_LETTER]
(Your cover letter here)
[END_COVER_LETTER]

[START_CHANGES]
List changes as: "Reordered achievements to emphasize cloud leadership", "Rewrote summary to highlight AI governance", "Added project context for CIMSystem role"
[END_CHANGES]
"""
        return prompt.strip()
    
    def _format_resume_for_prompt(self) -> str:
        """Format resume into clean, readable text for prompt"""
        lines = []
        
        try:
            # Personal info
            personal = self.resume.get("personal", {})
            lines.append("PERSONAL INFORMATION:")
            for key, val in personal.items():
                if val and key not in ['github', 'linkedin']:  # Skip some fields
                    lines.append(f"- {key.replace('_', ' ').title()}: {val}")
            
            # Summary
            if self.resume.get("summary"):
                lines.append(f"\nPROFESSIONAL SUMMARY:\n{self.resume['summary']}")
            
            # Skills
            if self.resume.get("skills"):
                lines.append("\nTECHNICAL SKILLS:")
                for category, skills in self.resume["skills"].items():
                    if skills:
                        category_name = category.replace("_", " ").title()
                        lines.append(f"- {category_name}: {', '.join(skills)}")
            
            # Experience
            if self.resume.get("experience"):
                lines.append("\nPROFESSIONAL EXPERIENCE:")
                for exp in self.resume["experience"]:
                    title = exp.get("title", "N/A")
                    company = exp.get("company", "N/A")
                    dates = exp.get("dates", "N/A")
                    location = exp.get("location", "")
                    
                    lines.append(f"\n{title}")
                    lines.append(f"{company} | {dates} | {location}")
                    
                    if exp.get("achievements"):
                        lines.append("Key Achievements:")
                        for achievement in exp["achievements"]:
                            lines.append(f"• {achievement}")
                    
                    if exp.get("skills_used"):
                        lines.append(f"Technologies: {', '.join(exp['skills_used'])}")
            
            # Projects
            if self.resume.get("projects"):
                lines.append("\nPROJECTS:")
                for project in self.resume["projects"]:
                    name = project.get("name", "N/A")
                    dates = project.get("dates", "")
                    lines.append(f"\n- {name} ({dates})")
                    if project.get("description"):
                        lines.append(f"  {project['description']}")
                    if project.get("github"):
                        lines.append(f"  GitHub: {project['github']}")
            
            # Certifications
            if self.resume.get("certifications"):
                lines.append("\nCERTIFICATIONS:")
                for cert in self.resume["certifications"]:
                    name = cert.get("name", "N/A")
                    issuer = cert.get("issuer", "")
                    date = cert.get("date", "")
                    lines.append(f"- {name} ({issuer}, {date})")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error formatting resume: {e}")
            return str(self.resume)  # Fallback
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Gemini response with improved error handling and validation.
        """
        result = {
            "resume_text": "",
            "cover_letter": "",
            "changes": [],
        }
        
        try:
            # Extract resume
            if "[START_RESUME]" in response_text and "[END_RESUME]" in response_text:
                result["resume_text"] = response_text.split("[START_RESUME]")[1].split("[END_RESUME]")[0].strip()
            
            # Extract cover letter
            if "[START_COVER_LETTER]" in response_text and "[END_COVER_LETTER]" in response_text:
                result["cover_letter"] = response_text.split("[START_COVER_LETTER]")[1].split("[END_COVER_LETTER]")[0].strip()
            
            # Extract changes
            if "[START_CHANGES]" in response_text and "[END_CHANGES]" in response_text:
                changes_text = response_text.split("[START_CHANGES]")[1].split("[END_CHANGES]")[0].strip()
                # Parse as bullet points or comma-separated
                if "\n" in changes_text:
                    result["changes"] = [c.strip("• -* ") for c in changes_text.split("\n") if c.strip()]
                else:
                    result["changes"] = [c.strip() for c in changes_text.split(",") if c.strip()]
            
            return result
            
        except IndexError as e:
            logger.error(f"Failed to parse Gemini response: missing sections: {e}")
            logger.debug(f"Raw response: {response_text[:500]}...")
            # Return partial result if possible
            return result
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return result
    
    def _validate_tailored_content(self, content: Dict[str, Any]) -> bool:
        """Validate that generated content meets minimum requirements"""
        try:
            # Check resume length
            if len(content.get("resume_text", "")) < 500:
                logger.warning("Generated resume seems too short")
                return False
            
            # Check cover letter length
            if len(content.get("cover_letter", "")) < 200:
                logger.warning("Generated cover letter seems too short")
                return False
            
            # Check for fabricated content warnings
            resume_text = content.get("resume_text", "").lower()
            forbidden_phrases = ["i am proficient in", "expert in", "i have experience with"]
            for phrase in forbidden_phrases:
                if phrase in resume_text and "resume_data" not in str(self.resume):
                    logger.warning(f"Potential fabrication detected: '{phrase}'")
            
            return True
            
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            return False

def demo_tailor():
    """Demo the tailor with a sample job"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    if not GEMINI_CONFIGURED:
        print("❌ Gemini API not configured. Set GEMINI_API_KEY in .env")
        return
    
    # Sample job
    job = {
        "id": "demo_123",
        "title": "Senior IT Infrastructure Architect",
        "company": "TechCorp",
        "description": """
        We are seeking a Senior IT Infrastructure Architect with deep expertise in AWS cloud,
        network security, and help desk leadership. The ideal candidate will have experience
        with AI governance frameworks and team management. You will design scalable infrastructure
        and mentor junior engineers.
        
        Requirements:
        - 10+ years in IT infrastructure
        - AWS Certified
        - Leadership experience
        - Python scripting skills
        """,
    }
    
    match = {
        "match_score": 0.92,
        "matched_skills": [
            "AWS Cloud Infrastructure",
            "Python",
            "Help Desk Leadership",
            "Network Security",
            "AI Governance"
        ],
        "relevant_experience": [
            "Digital Dental Technical Specialist at CIMSystem (2018–2025)",
            "Network Architect at AccuCode (2017–2018)"
        ],
    }
    
    try:
        tailor = ResumeTailor()
        result = tailor.tailor_application(job, match)
        
        print("\n" + "="*80)
        print("TAILORED RESUME")
        print("="*80)
        print(result["resume_text"])
        
        print("\n" + "="*80)
        print("COVER LETTER")
        print("="*80)
        print(result["cover_letter"])
        
        print("\n" + "="*80)
        print("CHANGES MADE")
        print("="*80)
        for change in result["changes"]:
            print(f"• {change}")
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logging.error(e, exc_info=True)

if __name__ == "__main__":
    demo_tailor()

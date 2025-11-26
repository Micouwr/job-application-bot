"""
Resume tailoring engine - Generates customized narratives for job applications using Gemini AI.
"""

import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from functools import wraps
from pathlib import Path

from google import genai
from google.genai import types
from google.genai.errors import APIError
from config.settings import RESUME_DATA, TAILORING
import tiktoken  # For token counting

logger = logging.getLogger(__name__)


class MaxRetriesExceeded(Exception):
    """✅ QoL: Custom exception for retry failures"""
    def __init__(self, message: str, original_error: Exception):
        self.message = message
        self.original_error = original_error
        super().__init__(f"{message}: {original_error}")


def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator for exponential backoff retry logic"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except APIError as e:
                    last_error = e
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise MaxRetriesExceeded(f"API call failed after {max_retries} retries", e)
                    
                    wait_time = delay * (2  ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
            
            # This should never be reached due to raise above, but explicit for clarity
            raise MaxRetriesExceeded(f"API call failed after {max_retries} retries", last_error)
        
        return wrapper
    return decorator


class ResumeTailor:
    """
    Tailor resume and cover letter for specific job applications using the Gemini AI API.
    """
    
    # Prompt templates for better maintainability
    PROMPT_TEMPLATE = """
**Objective:** Tailor the following resume and generate a cover letter for the given job description.

**Job Title:** {{job_title}}
**Company:** {{company}}
**Job Description:**
{{job_description}}

**Match Analysis:**
- Match Score: {{match_score}}%
- Matched Skills: {{matched_skills}}
- Relevant Experience: {{relevant_experience}}

**Resume:**
{{resume}}

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
    
    def __init__(self, resume: Dict):
        """Initialize with resume data and Gemini client"""
        self.resume = resume
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # For token counting
        
        # Initialize Gemini client with robust validation
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set or is empty")
        if not api_key.startswith("AIza"):
            raise ValueError("GEMINI_API_KEY must start with 'AIza'")
        
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_name = TAILORING["model"]
            logger.info(f"✓ Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None
            self.model_name = None
            raise

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text to avoid exceeding model limits"""
        return len(self.tokenizer.encode(text))

    def _validate_prompt(self, prompt: str) -> None:
        """Validate prompt doesn't exceed token limits"""
        token_count = self._count_tokens(prompt)
        max_tokens = TAILORING["max_tokens"]
        
        if token_count > 30000:  # Leave buffer for response
            logger.warning(f"Prompt is very large: {token_count} tokens")
            raise ValueError(f"Prompt too large: {token_count} tokens (max ~32k total)")

    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def tailor_application(self, job: Dict, match: Dict) -> Dict:
        """
        Generates a tailored resume and cover letter for a given job application.
        
        Args:
            job: Job dictionary with title, company, description
            match: Match results from JobMatcher
            
        Returns:
            Dictionary with resume_text, cover_letter, and changes
        """
        if not self.client or not self.model_name:
            raise RuntimeError("Gemini client not properly initialized")

        # Build and validate prompt
        prompt = self._build_prompt(job, match)
        self._validate_prompt(prompt)
        
        # Check cache first
        cache_key = self._get_cache_key(job, match)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info("✓ Using cached tailoring result")
            return cached_result
        
        try:
            logger.info(f"🤖 Generating tailored application for {job['title']}...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=TAILORING["temperature"],
                    top_p=1.0,
                    top_k=32,
                    max_output_tokens=TAILORING["max_tokens"],
                )
            )
            
            if not response or not hasattr(response, 'text') or not response.text:
                raise ValueError("Empty or invalid response from Gemini API")
                
            result = self._parse_response(response.text)
            self._save_to_cache(cache_key, result)
            return result
            
        except APIError as e:
            logger.error(f"Gemini API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during generation: {e}")
            raise

    async def tailor_application_stream(self, job: Dict, match: Dict) -> AsyncGenerator[str, None]:
        """
        Streaming version for real-time feedback.
        
        Yields chunks of the response as they arrive.
        """
        if not self.client or not self.model_name:
            raise RuntimeError("Gemini client not properly initialized")

        prompt = self._build_prompt(job, match)
        self._validate_prompt(prompt)
        
        try:
            stream = await self.client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=TAILORING["temperature"],
                    top_p=1.0,
                    top_k=32,
                    max_output_tokens=TAILORING["max_tokens"],
                )
            )
            
            async for chunk in stream:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise

    def _build_prompt(self, job: Dict, match: Dict) -> str:
        """Build prompt using template, escaping special characters"""
        resume_str = self._format_resume()
        
        # ✅ Fix: Escape braces in resume to prevent f-string issues
        resume_str = resume_str.replace("{", "{{").replace("}", "}}")
        
        # ✅ Fix: Escape braces in job title and other fields
        job_title = job.get('title', 'N/A').replace("{", "{{").replace("}", "}}")
        company = job.get('company', 'N/A').replace("{", "{{").replace("}", "}}")
        job_description = job.get('description', 'N/A').replace("{", "{{").replace("}", "}}")
        
        return self.PROMPT_TEMPLATE.replace(
            "{{job_title}}", job_title
        ).replace(
            "{{company}}", company
        ).replace(
            "{{job_description}}", job_description
        ).replace(
            "{{match_score}}", f"{match.get('match_score', 0)*100:.1f}"
        ).replace(
            "{{matched_skills}}", ', '.join(match.get('matched_skills', []))
        ).replace(
            "{{relevant_experience}}", '; '.join(match.get('relevant_experience', []))
        ).replace(
            "{{resume}}", resume_str
        )

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
        """Parse Gemini API response to extract sections."""
        try:
            # Extract sections using explicit parsing
            resume = self._extract_section(response_text, "[START_RESUME]", "[END_RESUME]")
            cover_letter = self._extract_section(response_text, "[START_COVER_LETTER]", "[END_COVER_LETTER]")
            changes_str = self._extract_section(response_text, "[START_CHANGES]", "[END_CHANGES]")
            
            # ✅ Fix: Handle empty changes properly
            changes = [c.strip() for c in changes_str.split(",") if c.strip()] if changes_str else []
            
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
        """Extract content between markers safely"""
        try:
            # Use find() which returns -1 instead of raising ValueError
            start = text.find(start_marker)
            if start == -1:
                logger.warning(f"Start marker '{start_marker}' not found")
                return ""
            
            start += len(start_marker)
            end = text.find(end_marker, start)
            if end == -1:
                logger.warning(f"End marker '{end_marker}' not found")
                return ""
            
            return text[start:end].strip()
        except Exception as e:
            logger.error(f"Error extracting section: {e}")
            return ""

    def _get_cache_key(self, job: Dict, match: Dict) -> str:
        """Generate cache key from job and match data"""
        cache_data = {
            "job_id": job.get("id"),
            "match_score": match.get("match_score"),
            "matched_skills": sorted(match.get("matched_skills", []))
        }
        return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached result"""
        # ✅ Fix: Use absolute path for cache
        cache_file = Path(__file__).parent.parent / "data" / "tailoring_cache.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
            return cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
            return None

    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Save result to cache"""
        # ✅ Fix: Use absolute path for cache
        cache_file = Path(__file__).parent.parent / "data" / "tailoring_cache.json"
        cache_file.parent.mkdir(exist_ok=True)
        
        try:
            cache = {}
            if cache_file.exists():
                with open(cache_file, "r") as f:
                    cache = json.load(f)
            
            cache[cache_key] = result
            
            with open(cache_file, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")


class AsyncResumeTailor(ResumeTailor):
    """Async version of ResumeTailor for concurrent processing"""
    
    async def tailor_application_async(self, job: Dict, match: Dict) -> Dict[str, Any]:
        """Async version with progress tracking"""
        # This would use asyncio and the streaming API
        # Implementation placeholder for now
        raise NotImplementedError("Async implementation coming soon")


# Demo usage with progress bar
if __name__ == "__main__":
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
        # Show progress bar
        from tqdm import tqdm  # Import here to avoid dependency in library mode
        with tqdm(total=1, desc="Generating") as pbar:
            result = tailor.tailor_application(job, match)
            pbar.update(1)
        
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

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader, Template

from config.settings import GEMINI_MODEL, OUTPUT_PATH

PROMPTS_DIR = Path(__file__).parent / "prompts" / "system"

def load_prompt_template(role_level="Standard"):
    """Load Jinja2 prompt template for role level."""
    env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))
    
    # Map roles to template files
    template_map = {
        "Standard": "system.txt.j2",
        "Senior": "senior.txt.j2",
        "Lead": "senior.txt.j2",
        "Principal": "senior.txt.j2"
    }
    
    template_name = template_map.get(role_level, "system.txt.j2")
    return env.get_template(template_name)

def load_user_prompt_template(prompt_name="custom_template.txt.j2"):
    """Load user-created prompt template."""
    user_prompts_dir = PROMPTS_DIR / "user"
    
    if not (user_prompts_dir / prompt_name).exists():
        return None
    
    env = Environment(loader=FileSystemLoader(str(user_prompts_dir)))
    return env.get_template(prompt_name)

def process_and_tailor_from_gui(resume_text, job_description, output_path, role_level="Standard", custom_prompt=None):
    """
    Process and tailor a resume for a job application from GUI.
    
    Args:
        resume_text: Text content of the resume
        job_description: Job description text
        output_path: Path where outputs will be saved
        role_level: Role level for template selection
        custom_prompt: Optional custom prompt template name
        
    Returns:
        Dict with resume_text and cover_letter keys
    """
    # Function verification removed for production
    
    try:
        # Load prompt template
        if custom_prompt:
            template = load_user_prompt_template(custom_prompt)
        else:
            template = load_prompt_template(role_level)
        
        if not template:
            raise Exception("Failed to load prompt template")
        
        # Template verification removed for production
        
        # Render prompt with variables
        prompt = template.render(
            role_level=role_level,
            company_name="Target Company",  # Placeholder - should extract from job_description
            job_title="Target Role",          # Placeholder - should extract from job_description
            job_description=job_description,
            resume_text=resume_text
        )
        
        # Prompt length check removed for production
        
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found in environment")
        
        # API initialization message removed for production
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # API call message removed for production
        response = model.generate_content(prompt)
        
        # Response length check removed for production
        
        # Parse response (extract resume and cover letter)
        response_text = response.text.strip()
        
        # Look for our delimiters
        if "[COVER LETTER]" in response_text and "[TAILORING_COMPLETE]" in response_text:
            # Extract content between delimiters
            start_idx = response_text.find("[TAILORING_COMPLETE]") + len("[TAILORING_COMPLETE]")
            cover_letter_idx = response_text.find("[COVER LETTER]")
            end_idx = response_text.find("[END_APPLICATION_MATERIALS]")
            
            if cover_letter_idx != -1 and end_idx != -1 and start_idx < cover_letter_idx < end_idx:
                resume_tailored = response_text[start_idx:cover_letter_idx].strip()
                cover_letter = response_text[cover_letter_idx + len("[COVER LETTER]"):end_idx].strip()
            else:
                # Fallback to simple splitting if delimiters are malformed
                parts = response_text.split("[COVER LETTER]", 1)
                resume_tailored = parts[0].replace("[TAILORING_COMPLETE]", "").strip()
                cover_letter = parts[1].replace("[END_APPLICATION_MATERIALS]", "").strip() if len(parts) > 1 else "Cover letter not generated."
        elif "\n\nCOVER LETTER:\n\n" in response_text:
            # Handle old format for backward compatibility
            sections = response_text.split("\n\nCOVER LETTER:\n\n")
            resume_tailored = sections[0].strip()
            cover_letter = sections[1].strip() if len(sections) > 1 else "Cover letter not generated."
        else:
            # If no clear delimiters, assume entire response is the resume
            resume_tailored = response_text
            cover_letter = "Cover letter not generated. Please try again or contact support."
        
        # Clean up any remaining delimiters
        resume_tailored = resume_tailored.replace("[TAILORING_COMPLETE]", "").strip()
        cover_letter = cover_letter.replace("[END_APPLICATION_MATERIALS]", "").strip()
        
        return {
            "resume_text": resume_tailored,
            "cover_letter": cover_letter
        }
        
    except Exception as e:
        raise

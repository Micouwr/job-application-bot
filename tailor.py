import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader, Template

from config.settings import GEMINI_MODEL, OUTPUT_PATH

PROMPTS_DIR = Path(__file__).parent / "prompts"

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
        
        # Parse response (split into resume and cover letter)
        sections = response.text.split("\n\nCOVER LETTER:\n\n")
            
        if len(sections) != 2:
            raise Exception("AI response not in expected format (missing COVER LETTER delimiter)")
            
        resume_tailored = sections[0].strip()
        cover_letter = sections[1].strip()
        
        return {
            "resume_text": resume_tailored,
            "cover_letter": cover_letter
        }
        
    except Exception as e:
        raise

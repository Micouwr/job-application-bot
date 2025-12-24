import os
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader, Template

from config.settings import GEMINI_MODEL, OUTPUT_PATH
from AI.match_analyzer import extract_job_details

PROMPTS_DIR = Path(__file__).parent / "prompts" / "system"

def load_prompt_template(role_level="Standard"):
    """Load Jinja2 prompt template for role level."""
    env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))
    
    # Map roles to template files
    template_map = {
        "Standard": "system.txt.j2",
        "Senior": "senior.txt.j2",
        "Lead": "lead.txt.j2",
        "Principal": "principal.txt.j2"
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
    logging.info(f"Starting tailoring process for role: {role_level}")
    
    try:
        # Load prompt template
        if custom_prompt:
            template = load_user_prompt_template(custom_prompt)
        else:
            template = load_prompt_template(role_level)
        
        if not template:
            raise Exception("Failed to load prompt template")
        
        logging.debug("Prompt template loaded successfully.")
        
        # Dynamically extract job title and company name
        try:
            job_details = extract_job_details(job_description)
            company_name = job_details.get("company_name", "Target Company")
            job_title = job_details.get("job_title", "Target Role")
        except Exception as e:
            logging.warning(f"Could not extract job details: {e}. Using placeholders.")
            company_name = "Target Company"
            job_title = "Target Role"

        # Render prompt with variables
        prompt = template.render(
            role_level=role_level,
            company_name=company_name,
            job_title=job_title,
            job_description=job_description,
            resume_text=resume_text
        )
        
        logging.info(f"Generated prompt of length {len(prompt)} characters.")
        
        # Initialize Gemini with timeout settings
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        logging.info(f"Configured Gemini with model: {GEMINI_MODEL}")
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        logging.info("Sending request to Gemini API...")
        # Add timeout to prevent hanging
        response = model.generate_content(prompt, request_options={'timeout': 120})
        
        logging.info("Received response from Gemini API.")
        
        # Parse JSON response
        try:
            response_text = response.text.strip()
            
            # Remove markdown code block markers if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_json = json.loads(response_text)

            resume_tailored = response_json.get("tailored_resume", "")
            cover_letter = response_json.get("cover_letter", "")

            if not resume_tailored or not cover_letter:
                raise ValueError("Missing 'tailored_resume' or 'cover_letter' in AI response.")

        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Failed to parse AI response as JSON: {e}\nRaw response: {response.text}")
            # Fallback for safety, though it should not be needed with the new prompt
            resume_tailored = response.text
            cover_letter = "Cover letter not generated due to a parsing error."

        return {
            "resume_text": resume_tailored.strip(),
            "cover_letter": cover_letter.strip()
        }
        
    except Exception as e:
        raise

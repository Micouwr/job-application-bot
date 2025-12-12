import google.generativeai as genai
import os
import re
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from config.settings import OUTPUT_PATH
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import os

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


def process_and_tailor_from_gui(job_title, company, job_description, job_url, resume_text, applicant_name="Applicant"):
    """
    Process and tailor resume from GUI inputs
    """
    # Load API key
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise Exception("Gemini API key not found. Please set GEMINI_API_KEY in .env file")
    
    genai.configure(api_key=api_key)
    
    # Create prompt
    prompt = f"""
    You are an expert resume and cover letter writer. Create a tailored resume and cover letter based on the following information:
    
    APPLICANT NAME: {applicant_name}
    JOB TITLE: {job_title}
    COMPANY: {company}
    JOB DESCRIPTION: {job_description}
    JOB URL: {job_url}
    
    EXISTING RESUME:
    {resume_text}
    
    Please provide:
    1. A tailored resume optimized for this position
    2. A customized cover letter
    
    Format your response as JSON with keys "resume_text" and "cover_letter".
    """
    
    # Call Gemini API
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    
    # Parse response
    try:
        # Extract JSON from response
        response_text = response.text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if json_match:
            result = json.loads(json_match.group())
            return {
                "resume_text": result.get("resume_text", ""),
                "cover_letter": result.get("cover_letter", "")
            }
        else:
            # Fallback if JSON not found
            return {
                "resume_text": response_text,
                "cover_letter": "Cover letter generation failed - see resume text"
            }
            
    except Exception as e:
        raise Exception(f"Failed to parse AI response: {e}")

if __name__ == "__main__":
    print("Tailor module loaded successfully")

import os
import google.generativeai as genai
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment from project root
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

DIAGNOSTIC_MODE = False

def analyze_match(resume_text: str, job_description: str) -> dict:
    """Core AI function: Compare resume to job description and return match analysis."""
    # Diagnostic mode disabled for production
    
    # Verify API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise Exception("GEMINI_API_KEY not configured")
    
    # Configure Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        raise
    
    # Build analysis prompt
    prompt = f"""
    Analyze this resume against the job description and provide a detailed match analysis.
    Return ONLY a valid JSON object with these exact keys: overall_score, skills_match, experience_match, keywords_match, recommendations, strengths, gaps.
    
    The skills_match, experience_match, and keywords_match should each be objects with 'score' (integer 0-100) and 'analysis' (array of strings) keys.
    The recommendations, strengths, and gaps should each be arrays of strings.
    
    Example format:
    {{
        "overall_score": 85,
        "skills_match": {{
            "score": 90,
            "analysis": [
                "Strong match in Python and JavaScript",
                "Good match in SQL proficiency"
            ]
        }},
        "experience_match": {{
            "score": 80,
            "analysis": [
                "5+ years in AI development matches requirement",
                "Experience with GPT APIs is directly relevant"
            ]
        }},
        "keywords_match": {{
            "score": 88,
            "analysis": [
                "Keywords 'Python', 'JavaScript', 'SQL' found in both",
                "'GPT APIs' and 'PyInstaller' are highly relevant"
            ]
        }},
        "recommendations": [
            "Consider highlighting project management experience more prominently",
            "Add specific metrics to quantify achievements"
        ],
        "strengths": [
            "Strong technical skills alignment with job requirements",
            "Relevant experience in AI development"
        ],
        "gaps": [
            "Limited explicit project management experience mentioned",
            "No specific metrics provided for achievements"
        ]
    }}
    
    RESUME:
    {resume_text}
    
    JOB DESCRIPTION:
    {job_description}
    """
    
    # Call Gemini API
    try:
        response = model.generate_content(prompt)
        
        # Parse JSON response (strip markdown if present)
        try:
            response_text = response.text.strip()
            
            # Remove markdown code block markers
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove ```
            
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse AI response as JSON: {e}")
    
    except Exception as e:
        raise

def extract_job_details(job_description: str) -> dict:
    """Extract job title and company name from job description using AI."""
    # Verify API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise Exception("GEMINI_API_KEY not configured")
    
    # Configure Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        raise
    
    # Build extraction prompt
    prompt = f"""
    Extract the job title and company name from this job description.
    Return ONLY a valid JSON object with these exact keys: job_title, company_name
    
    If you cannot determine either value, use "Unknown" as the value.
    
    Example format:
    {{
        "job_title": "Software Engineer",
        "company_name": "Tech Corp"
    }}
    
    JOB DESCRIPTION:
    {job_description}
    """
    
    # Call Gemini API
    try:
        response = model.generate_content(prompt)
        
        # Parse JSON response (strip markdown if present)
        try:
            response_text = response.text.strip()
            
            # Remove markdown code block markers
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove ```
            
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return defaults
            return {
                "job_title": "Unknown",
                "company_name": "Unknown"
            }
    
    except Exception as e:
        # If API call fails, return defaults
        return {
            "job_title": "Unknown",
            "company_name": "Unknown"
        }

# Self-test when module is run directly
if __name__ == "__main__":
    if DIAGNOSTIC_MODE:
        print("[DIAGNOSTIC] Running self-test...")
    
    # Built-in test data (no separate files)
    test_resume = """
    Michelle Nicole
    AI Developer & Automation Specialist
    San Francisco, CA
    
    Professional Summary:
    5 years experience building AI-powered applications using Python, GPT APIs, and PyInstaller.
    
    Technical Skills:
    Python, JavaScript, SQL, Google Generative AI, PyInstaller, SQLite, REST APIs
    
    Experience:
    Senior AI Developer at Tech Innovations Inc. (2022-Present)
    - Developed AI-powered resume tailoring system using GPT-4 API
    - Implemented cross-platform desktop applications for 500+ users
    - Built automated job application bot using Gemini API
    
    Certifications:
    - Two AI certifications (Google, AWS)
    """
    
    test_job = """
    AI Learning Design Lead
    Healthcare Company
    
    Responsibilities:
    Design, develop, and deliver strategic learning experiences supporting AI initiatives.
    Analyze content, write storyboards, partner with subject matter experts.
    
    Requirements:
    - 5+ years experience in AI/ML development
    - Python, JavaScript, SQL proficiency
    - Experience with GPT APIs and PyInstaller
    - Strong consultative and project management skills
    """
    
    try:
        if DIAGNOSTIC_MODE:
            print("[DIAGNOSTIC] Testing AI match analysis...")
        result = analyze_match(test_resume, test_job)
        
        if DIAGNOSTIC_MODE:
            print("\n[DIAGNOSTIC] Test completed successfully!")
            print(f"Overall Match Score: {result.get('overall_score', 'N/A')}%")
            print(f"Skills Match: {result.get('skills_match', 'N/A')}%")
            print(f"Experience Match: {result.get('experience_match', 'N/A')}%")
            print(f"Keywords Match: {result.get('keywords_match', 'N/A')}%")
            print(f"\nRecommendations: {result.get('recommendations', [])}")
            print(f"Strengths: {result.get('strengths', [])}")
            print(f"Gaps: {result.get('gaps', [])}")
        
    except Exception as e:
        if DIAGNOSTIC_MODE:
            print(f"\n[DIAGNOSTIC] Test FAILED: {e}")
        raise

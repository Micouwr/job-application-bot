import os
import google.generativeai as genai
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment from project root
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

DIAGNOSTIC_MODE = True

def analyze_match(resume_text: str, job_description: str) -> dict:
    """Core AI function: Compare resume to job description and return match analysis."""
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] analyze_match called")
        print(f"[DIAGNOSTIC] Resume length: {len(resume_text)} chars")
        print(f"[DIAGNOSTIC] Job description length: {len(job_description)} chars")
    
    # Verify API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        if DIAGNOSTIC_MODE:
            print("[DIAGNOSTIC] ERROR: GEMINI_API_KEY not configured")
        raise Exception("GEMINI_API_KEY not configured")
    
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] API key found: {api_key[:8]}...")
    
    # Configure Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        if DIAGNOSTIC_MODE:
            print("[DIAGNOSTIC] Gemini model initialized")
    except Exception as e:
        if DIAGNOSTIC_MODE:
            print(f"[DIAGNOSTIC] ERROR initializing Gemini: {e}")
        raise
    
    # Build analysis prompt
    prompt = f"""
    Analyze this resume against the job description and provide a detailed match analysis.
    Return ONLY a JSON object with these exact keys: overall_score, skills_match, experience_match, keywords_match, recommendations, strengths, gaps.
    Scores should be integers 0-100.
    All list values should be strings.
    
    RESUME:
    {resume_text}
    
    JOB DESCRIPTION:
    {job_description}
    """
    
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] Generated prompt, length: {len(prompt)} chars")
    
    # Call Gemini API
    try:
        if DIAGNOSTIC_MODE:
            print("[DIAGNOSTIC] Calling Gemini API...")
        
        response = model.generate_content(prompt)
        
        if DIAGNOSTIC_MODE:
            print(f"[DIAGNOSTIC] API response received, length: {len(response.text)} chars")
        
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
            
            if DIAGNOSTIC_MODE:
                print(f"[DIAGNOSTIC] Cleaned response text: {response_text[:100]}...")
            
            result = json.loads(response_text)
            
            if DIAGNOSTIC_MODE:
                print(f"[DIAGNOSTIC] Parsed JSON successfully")
                print(f"[DIAGNOSTIC] Overall score: {result.get('overall_score', 'N/A')}")
            return result
        except json.JSONDecodeError as e:
            if DIAGNOSTIC_MODE:
                print(f"[DIAGNOSTIC] ERROR parsing JSON: {e}")
                print(f"[DIAGNOSTIC] Raw response: {response.text[:200]}...")
            raise Exception(f"Failed to parse AI response as JSON: {e}")
    
    except Exception as e:
        if DIAGNOSTIC_MODE:
            print(f"[DIAGNOSTIC] ERROR during API call: {e}")
        raise

# Self-test when module is run directly
if __name__ == "__main__":
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
        print("[DIAGNOSTIC] Testing AI match analysis...")
        result = analyze_match(test_resume, test_job)
        
        print("\n[DIAGNOSTIC] Test completed successfully!")
        print(f"Overall Match Score: {result.get('overall_score', 'N/A')}%")
        print(f"Skills Match: {result.get('skills_match', 'N/A')}%")
        print(f"Experience Match: {result.get('experience_match', 'N/A')}%")
        print(f"Keywords Match: {result.get('keywords_match', 'N/A')}%")
        print(f"\nRecommendations: {result.get('recommendations', [])}")
        print(f"Strengths: {result.get('strengths', [])}")
        print(f"Gaps: {result.get('gaps', [])}")
        
    except Exception as e:
        print(f"\n[DIAGNOSTIC] Test FAILED: {e}")
        raise

import os
import google.generativeai as genai

DIAGNOSTIC_MODE = True

def tailor_resume(resume_text: str, job_description: str, match_data: dict) -> str:
    """
    Generate tailored resume using ONLY factual information from original resume.
    
    Rules:
    1. Only use content that exists in resume_text
    2. Reorder bullet points based on job_description priority
    3. No fluff, no hallucination
    4. Optimize for ATS keywords from job_description
    """
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] tailor_resume called")
        print(f"[DIAGNOSTIC] Resume length: {len(resume_text)} chars")
        print(f"[DIAGNOSTIC] Match score: {match_data.get('overall_score', 'N/A')}%")
    
    # Verify API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        if DIAGNOSTIC_MODE:
            print("[DIAGNOSTIC] ERROR: GEMINI_API_KEY not configured")
        raise Exception("GEMINI_API_KEY not configured")
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Build tailoring prompt
    prompt = f"""
    Tailor this resume for the job description using ONLY factual information from the resume.
    
    RESUME (use only this content - do not add new information):
    {resume_text}
    
    JOB DESCRIPTION (use for priority and keywords):
    {job_description}
    
    MATCH ANALYSIS (use for guidance):
    {match_data}
    
    RULES:
    1. Only use facts from the resume - NO new information
    2. Reorder points to match job priority
    3. No fluff, no hallucination
    4. Optimize for ATS keywords from job description
    5. Keep factual tone - don't oversell
    6. Preserve original accomplishments and metrics
    
    Return ONLY the tailored resume text.
    """
    
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] Generated tailoring prompt, length: {len(prompt)} chars")
        print(f"[DIAGNOSTIC] Calling Gemini API for tailoring...")
    
    response = model.generate_content(prompt)
    
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] Tailoring response received, length: {len(response.text)} chars")
    
    return response.text.strip()

def generate_cover_letter(resume_text: str, job_description: str, match_data: dict) -> str:
    """
    Generate cover letter using ONLY information from resume.
    
    Rules:
    1. Three paragraphs maximum
    2. Reference specific achievements from resume with metrics
    3. Connect resume experience to job requirements
    4. Professional, concise tone
    5. No generic statements
    """
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] generate_cover_letter called")
    
    # Verify API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        if DIAGNOSTIC_MODE:
            print("[DIAGNOSTIC] ERROR: GEMINI_API_KEY not configured")
        raise Exception("GEMINI_API_KEY not configured")
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Write a professional cover letter for this job using ONLY information from the resume.
    
    RESUME (reference specific achievements and metrics):
    {resume_text}
    
    JOB DESCRIPTION (connect experience to requirements):
    {job_description}
    
    MATCH ANALYSIS (use for positioning):
    {match_data}
    
    RULES:
    1. Maximum 3 paragraphs
    2. Reference specific resume achievements with metrics
    3. Connect past experience to job requirements
    4. Professional, concise tone
    5. No generic statements
    
    Return ONLY the cover letter text.
    """
    
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] Generated cover letter prompt, length: {len(prompt)} chars")
        print(f"[DIAGNOSTIC] Calling Gemini API for cover letter...")
    
    response = model.generate_content(prompt)
    
    if DIAGNOSTIC_MODE:
        print(f"[DIAGNOSTIC] Cover letter response received, length: {len(response.text)} chars")
    
    return response.text.strip()

# Test both functions when run directly
if __name__ == "__main__":
    print("\n=== AI ENGINE SELF-TEST ===\n")
    
    # Reuse test data from match_analyzer
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
        # Import match analyzer
        from .match_analyzer import analyze_match
        
        print("1. Analyzing match...")
        match_data = analyze_match(test_resume, test_job)
        print(f"\nMatch Score: {match_data.get('overall_score', 'N/A')}%")
        
        print("\n2. Tailoring resume...")
        tailored = tailor_resume(test_resume, test_job, match_data)
        print(f"\nTailored resume generated ({len(tailored)} chars)")
        
        print("\n3. Generating cover letter...")
        cover_letter = generate_cover_letter(test_resume, test_job, match_data)
        print(f"\nCover letter generated ({len(cover_letter)} chars)")
        
        print("\n=== TEST COMPLETED SUCCESSFULLY ===")
        
    except Exception as e:
        print(f"\n[DIAGNOSTIC] Test FAILED: {e}")
        raise

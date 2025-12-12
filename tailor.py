import google.generativeai as genai
import os
import re
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

class ResumeTailor:
    def __init__(self, resume_data: dict):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file.")
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.resume_text = resume_data.get("full_text", "")
        self.applicant_name = resume_data.get("name", "Applicant")

    def generate_tailored_resume(self, job_description: str, job_title: str, company: str) -> dict:
        """
        Generates a tailored resume and cover letter using the Gemini API.
        """
        prompt = f"""
        You are an expert resume and cover letter writer. Create a tailored resume and cover letter based on the following information:

        APPLICANT NAME: {self.applicant_name}
        JOB TITLE: {job_title}
        COMPANY: {company}
        JOB DESCRIPTION: {job_description}

        EXISTING RESUME:
        {self.resume_text}

        Please provide:
        1. A tailored resume optimized for this position.
        2. A customized cover letter.

        Format your response as a single JSON object with two keys: "resume_text" and "cover_letter".
        """

        try:
            response = self.model.generate_content(prompt)
            # Basic cleaning to find the JSON blob
            cleaned_text = response.text.strip().lstrip("```json").rstrip("```")
            result = json.loads(cleaned_text)
            return {
                "success": True,
                "resume_text": result.get("resume_text", ""),
                "cover_letter": result.get("cover_letter", "")
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to parse AI response: {e}"}

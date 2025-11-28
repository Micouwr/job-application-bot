"""
Resume tailoring engine - Generates tailored resumes using AI.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json # Added for structured output parsing

from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

# CRITICAL FIX: Assume necessary globals are imported from config.settings
try:
    from config.settings import RESUME_DATA, AI_CONFIG, OUTPUT_PATH
except ImportError:
    # Placeholder definitions for standalone execution/review if config is not available
    AI_CONFIG = {"api_key": "YOUR_API_KEY", "model": "gemini-2.5-flash"}
    # RESUME_DATA must be provided or mocked. Using the structure implied by the resume text:
    RESUME_DATA = {
        "name": "William Ryan Micou",
        "title": "AI GOVERNANCE & TECHNICAL STRATEGY LEAD",
        "contact": {
            "phone": "(502) 777-7526",
            "email": "micouwr2025@gmail.com",
            "linkedin": "linkedin.com/in/ryanmicou",
            "location": "Louisville, KY"
        },
        "summary": "Strategic IT Operations Leader with 20+ years of experience modernizing technical environments...",
        "core_competencies": {
            "AI & Governance": ["ISO/IEC 42001 Standards", "Generative AI Strategy", "Responsible AI Frameworks", "Risk Management"],
            "Operational Leadership": ["Service Desk Automation", "SLA Optimization", "Vendor Management", "Strategic Planning"],
            "Technical Enablement": ["Knowledge Base Architecture", "Workflow Analysis", "Python (Automation)", "KPI Reporting"],
            "Infrastructure Foundation": ["Network Security Protocols", "Identity & Access Management (AD/LDAP)", "SaaS Administration"]
        },
        "experience": [
            {"company": "CIMSYSTEM", "title": "Technical Operations Lead & Specialist", "dates": "2018 – 2025", "location": "Louisville, KY", "achievements": ["Directed support operations for ~150 dealer partners...", "Led a 10-person support unit, achieving 99% uptime...", "Built 'MillBox 101' onboarding and centralized SOP library...", "Presented technical strategy sessions..."]},
            # ... other experiences must be structured similarly
        ],
        "education": [{"degree": "Front-End Web Development", "school": "Sullivan University (CodeLouisville Graduate)"}],
        "certifications": ["AI Management System Fundamentals (ISO/IEC 42001:2023)", "CompTIA A+"]
    }
    OUTPUT_PATH = Path('.')
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class JobAnalysis:
    """Structured data for job description analysis"""
    title: str = ""
    required_skills: List[str] = field(default_factory=list)
    experience_level: str = ""
    key_responsibilities: List[str] = field(default_factory=list)
    industry: str = ""
    special_requirements: List[str] = field(default_factory=list)


@dataclass
class TailoringResult:
    """Result of resume tailoring operation"""
    success: bool
    tailored_content: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    sections_generated: int = 0


class ResumeTailor:
    """
    AI-powered resume tailoring engine
    Generates customized resumes based on job descriptions
    """
    
    def __init__(self, resume_data: Dict = None):
        self.resume = resume_data or RESUME_DATA
        self.client = genai.Client(
            api_key=AI_CONFIG["api_key"],
            http_options=HttpOptions(api_version="v1")
        )
        
        # Removed tiktoken. Token counting will rely on the API response.
        self.model_name = AI_CONFIG["model"]
        logger.info("✓ ResumeTailor initialized with AI model")

    # Removed count_tokens method

    def _parse_job_analysis(self, raw_analysis: str) -> JobAnalysis:
        """Parses the raw structured text output into a JobAnalysis object."""
        try:
            # Simple text parsing assuming key: [list] or key: value structure
            data = {}
            current_key = None
            
            for line in raw_analysis.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Check for list items (start with - or *)
                if line.startswith(('-', '*')):
                    if current_key and current_key in data and isinstance(data[current_key], list):
                        data[current_key].append(line[1:].strip())
                    continue
                
                # Check for key: value
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().replace(" ", "_").lower()
                    value = value.strip()
                    
                    if key in ['required_technical_skills', 'key_responsibilities', 'special_requirements']:
                        current_key = key
                        data[key] = [value] if value else []
                    else:
                        current_key = key
                        data[key] = value
            
            # Map parsed data to JobAnalysis dataclass
            return JobAnalysis(
                title=data.get('primary_role/title', ''),
                required_skills=data.get('required_technical_skills', []),
                experience_level=data.get('experience_level', ''),
                key_responsibilities=data.get('key_responsibilities', []),
                industry=data.get('industry/sector', ''),
                special_requirements=data.get('special_requirements_or_preferences', []),
            )
        except Exception as e:
            logger.error(f"Failed to parse job analysis: {e}")
            return JobAnalysis()

    def analyze_job_description(self, job_text: str) -> Dict[str, Any]:
        """
        Analyze job description and extract key requirements, returning structured data.
        """
        prompt = f"""
        Analyze this job description and provide a structured analysis.
        
        Job Description:
        {job_text}
        
        Provide your analysis in a plain key: value or key: list format. Use simple bullet points (-) for lists.
        
        Format MUST be:
        Primary Role/Title: [Title]
        Required Technical Skills:
        - [Skill 1]
        - [Skill 2]
        Experience Level: [junior/mid/senior]
        Key Responsibilities:
        - [Responsibility 1]
        - [Responsibility 2]
        Industry/Sector: [Industry]
        Special Requirements or Preferences:
        - [Requirement 1]
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1000
                )
            )
            
            raw_analysis = response.text
            analysis_obj = self._parse_job_analysis(raw_analysis)
            
            # CRITICAL FIX: Retrieve tokens used directly from response
            tokens_used = (
                response.usage_metadata.prompt_token_count + 
                response.usage_metadata.candidates_token_count
            )
            
            logger.info("✓ Job description analysis completed")
            return {"analysis_obj": analysis_obj, "tokens_used": tokens_used}
            
        except Exception as e:
            logger.error(f"Job analysis failed: {e}")
            return {"error": str(e)}

    def generate_summary(self, job_analysis: JobAnalysis) -> Dict[str, Any]:
        """Generate a customized professional summary"""
        
        # Use the actual summary from the user's updated profile
        base_summary = self.resume.get("summary", "")
        
        prompt = f"""
        Generate a compelling professional summary (3-4 sentences) tailored to the requirements of the job.
        
        Prioritize and integrate the user's existing background and new AI certifications (ISO 42001) where they align with the job's needs.
        
        The user's core strengths are: {base_summary}
        The job requires: {job_analysis.key_responsibilities}, Skills: {job_analysis.required_skills}, Level: {job_analysis.experience_level}
        
        Generate ONLY the summary text, no labels or formatting.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=300
                )
            )
            
            summary = response.text.strip()
            
            tokens_used = (
                response.usage_metadata.prompt_token_count + 
                response.usage_metadata.candidates_token_count
            )
            
            logger.info("✓ Generated customized summary")
            return {"summary": summary, "tokens_used": tokens_used}
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return {"summary": base_summary, "tokens_used": 0}

    def tailor_experience(self, job_analysis: JobAnalysis) -> List[Dict[str, Any]]:
        """Tailor experience section to highlight relevant roles and achievements"""
        relevant_experience = []
        
        for exp in self.resume.get("experience", []):
            
            # CRITICAL FIX: Ensure achievement list is processed correctly
            achievements_list = exp.get("achievements", [])
            
            # Step 1: Calculate relevance score based on keywords and skills
            relevance_score = self._calculate_experience_relevance(exp, job_analysis)
            
            if relevance_score > 0.3: # Only include moderately relevant experience
                tailored_exp = {
                    "title": exp["title"],
                    "company": exp["company"],
                    "dates": exp["dates"],
                    "location": exp.get("location", ""),
                    "relevance_score": relevance_score
                }
                
                # Step 2: Generate tailored achievements for this role using LLM
                if achievements_list:
                    result = self._tailor_achievements(
                        exp["title"], exp["company"], achievements_list, job_analysis
                    )
                    tailored_exp["achievements"] = result["achievements"]
                    # Add tokens used in this sub-call
                    tailored_exp["tokens_used"] = result["tokens_used"]
                
                relevant_experience.append(tailored_exp)
        
        # Sort by relevance score (descending)
        relevant_experience.sort(key=lambda x: x["relevance_score"], reverse=True)
        logger.info(f"✓ Tailored {len(relevant_experience)} experience entries")
        return relevant_experience

    def _calculate_experience_relevance(self, exp: Dict, job_analysis: JobAnalysis) -> float:
        """Calculate relevance score for an experience entry"""
        score = 0.0
        
        # Combine job requirements into a single searchable string
        job_search_text = " ".join(
            [job_analysis.title.lower()] + job_analysis.required_skills + job_analysis.key_responsibilities
        )
        
        # Title relevance
        if any(keyword in exp["title"].lower() for keyword in job_search_text.split()):
            score += 0.4
        
        # Skill and Achievement relevance (check if any achievement bullet point contains required skills)
        for achievement in exp.get("achievements", []):
            if any(skill.lower() in achievement.lower() for skill in job_analysis.required_skills):
                score += 0.1
        
        # Experience type relevance (e.g., Service Desk/Infrastructure roles for this user)
        if any(keyword in exp["title"].lower() for keyword in ["service desk", "infrastructure", "network", "support"]):
            if any(keyword in job_search_text for keyword in ["service desk", "support", "network", "ops"]):
                score += 0.2
        
        return min(score, 1.0)

    def _tailor_achievements(
        self, 
        exp_title: str, 
        exp_company: str, 
        achievements: List[str], 
        job_analysis: JobAnalysis
    ) -> Dict[str, Any]:
        """
        CRITICAL FIX: Use LLM to rephrase and select most relevant achievements.
        """
        achievements_str = "\n".join([f"- {a}" for a in achievements])
        
        prompt = f"""
        You are a resume editor. The user has the following achievements for the role '{exp_title}' at '{exp_company}':
        {achievements_str}
        
        The target job requires expertise in: {job_analysis.required_skills} and focuses on: {job_analysis.key_responsibilities}.
        
        1. Select the 3 achievements that are MOST relevant to the target job.
        2. Rephrase them slightly to emphasize impact, quantification, and technical skills requested by the target job.
        3. Do not invent facts. Maintain the core meaning of the original achievement.
        
        Output ONLY the final 3 achievements as a numbered list.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=500
                )
            )
            
            # Simple line parsing to extract list items
            tailored_achievements = [
                line.strip()[3:].strip() # Remove "1. " or "- "
                for line in response.text.split('\n') 
                if re.match(r'^\s*[\-\d]+\.?\s+', line) and line.strip()
            ]

            tokens_used = (
                response.usage_metadata.prompt_token_count + 
                response.usage_metadata.candidates_token_count
            )
            
            return {"achievements": tailored_achievements, "tokens_used": tokens_used}
            
        except Exception as e:
            logger.error(f"Achievement tailoring failed: {e}")
            # Fallback
            return {"achievements": achievements[:3], "tokens_used": 0}

    def generate_technical_skills(self, job_analysis: JobAnalysis) -> Dict[str, Any]:
        """Generate a tailored technical skills section"""
        
        # CRITICAL FIX: Use actual structured core competencies from the resume
        resume_skills_flat = []
        for category, skills in self.resume.get("core_competencies", {}).items():
            # Add category and skills
            resume_skills_flat.extend(skills)
            
        # Prioritize skills mentioned in job description
        prioritized_skills = []
        analysis_text = " ".join(job_analysis.required_skills).lower()
        
        for skill in resume_skills_flat:
            if skill.lower() in analysis_text or any(kw in skill.lower() for kw in analysis_text.split()):
                prioritized_skills.append(skill)
        
        # Add the unique, unprioritized skills up to a max limit
        remaining_skills = [s for s in resume_skills_flat if s not in prioritized_skills]
        
        # Keep a max of 20 skills total
        final_skills = prioritized_skills + remaining_skills
        
        # Simple placeholder for tokens used (since no LLM call here)
        return {"skills": list(set(final_skills))[:20], "tokens_used": 0}

    def generate_tailored_resume(
        self, 
        job_description: str, 
        output_format: str = "markdown",
        include_sections: List[str] = None
    ) -> TailoringResult:
        """
        Generate a complete tailored resume
        """
        logger.info("🚀 Starting resume tailoring process...")
        total_tokens_used = 0
        
        try:
            # Step 1: Analyze job description
            logger.info("📋 Analyzing job description...")
            analysis_result = self.analyze_job_description(job_description)
            total_tokens_used += analysis_result.get("tokens_used", 0)
            
            if "error" in analysis_result:
                return TailoringResult(
                    success=False,
                    error=f"Job analysis failed: {analysis_result['error']}"
                )
            job_analysis: JobAnalysis = analysis_result["analysis_obj"]
            
            # Step 2: Generate tailored sections
            logger.info("✨ Generating tailored sections...")
            sections = {}
            sections_generated = 0
            
            # Professional Summary
            summary_result = self.generate_summary(job_analysis)
            sections["summary"] = summary_result["summary"]
            total_tokens_used += summary_result["tokens_used"]
            sections_generated += 1
            
            # Technical Skills
            skills_result = self.generate_technical_skills(job_analysis)
            sections["skills"] = skills_result["skills"]
            sections_generated += 1
            
            # Experience
            experience_list = self.tailor_experience(job_analysis)
            sections["experience"] = experience_list
            # Sum up tokens from all tailored achievement sub-calls
            total_tokens_used += sum(exp.get("tokens_used", 0) for exp in experience_list)
            sections_generated += 1
            
            # Education (keep as-is)
            sections["education"] = self.resume.get("education", [])
            
            # Certifications (keep as-is)
            sections["certifications"] = self.resume.get("certifications", [])
            
            # Projects (keep as-is) - Added since the user's resume has a strong project section
            sections["projects"] = self.resume.get("projects", [])
            
            # Step 3: Compile final resume
            logger.info("📄 Compiling final resume...")
            if output_format == "markdown":
                resume_content = self._compile_markdown_resume(sections)
            else:
                resume_content = self._compile_text_resume(sections)
            
            # Step 4: Count final content tokens and save
            # NOTE: We skip counting the final output content tokens since they are already counted 
            # as candidates_token_count in the generation steps.
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_hash = hashlib.md5(job_description[:100].encode()).hexdigest()[:8]
            # Use the job analysis title for a more readable filename
            filename_title = job_analysis.title.split()[0].replace('/', '_') if job_analysis.title else "job"
            filename = f"tailored_resume_{filename_title}_{timestamp}_{file_hash}.md"
            file_path = OUTPUT_PATH / filename
            
            # Save file
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(resume_content)
            
            logger.info(f"✅ Resume tailoring completed: {file_path}")
            return TailoringResult(
                success=True,
                tailored_content=resume_content,
                file_path=str(file_path),
                tokens_used=total_tokens_used,
                sections_generated=sections_generated
            )
            
        except Exception as e:
            logger.error(f"❌ Resume tailoring failed: {e}")
            return TailoringResult(
                success=False,
                error=str(e)
            )

    def _compile_markdown_resume(self, sections: Dict[str, Any]) -> str:
        """Compile sections into markdown format"""
        content = []
        
        # Header (Using name and title from resume data)
        content.append(f"# {self.resume.get('name', 'Professional Resume')}")
        content.append(f"**{self.resume.get('title', 'Experienced Professional')}**")
        
        # Contact info
        contact = self.resume.get("contact", {})
        contact_line = " | ".join([
            contact.get("location", ""), 
            contact.get("phone", ""), 
            contact.get("email", ""), 
            contact.get("linkedin", "")
        ]).strip(" | ")
        if contact_line:
            content.append(contact_line)
        content.append("---")
        
        # Summary
        content.append("## PROFESSIONAL SUMMARY")
        content.append(sections["summary"])
        content.append("")
        
        # Technical Skills
        content.append("## CORE COMPETENCIES")
        # Assuming the skills section from the resume is a list of strings
        skills_text = " | ".join(sections["skills"])
        content.append(skills_text)
        content.append("")
        
        # Technical Projects (New section for user's AI project)
        if self.resume.get("projects"):
             content.append("## TECHNICAL PROJECTS & INNOVATION")
             # Assuming projects is a list of structured data, compile a simple list
             for project in self.resume["projects"]:
                 content.append(f"### {project.get('name', '')} | {project.get('dates', '')}")
                 content.append(f"_{project.get('details', '')}_")
                 for bullet in project.get('achievements', []):
                    content.append(f"- {bullet}")
             content.append("")
        
        # Experience
        content.append("## PROFESSIONAL EXPERIENCE")
        for exp in sections["experience"]:
            content.append(f"### {exp['title']}")
            content.append(f"**{exp['company']}** | {exp['dates']}")
            if exp.get("location"):
                content.append(f"*{exp['location']}*")
            
            if "achievements" in exp:
                for achievement in exp["achievements"]:
                    content.append(f"- {achievement}")
            content.append("")
        
        # Education & Certifications
        content.append("---")
        content.append("## EDUCATION & CERTIFICATIONS")
        
        if sections["certifications"]:
            content.append("### Certifications")
            for cert in sections["certifications"]:
                content.append(f"- {cert}")
        
        if sections["education"]:
            content.append("### Education")
            for edu in sections["education"]:
                content.append(f"- {edu.get('degree', '')} - {edu.get('school', '')}")
            
        
        return "\n".join(content)

    def _compile_text_resume(self, sections: Dict[str, Any]) -> str:
        """Compile sections into plain text format"""
        # Falls back to markdown for simplicity
        return self._compile_markdown_resume(sections)


def demo_tailoring():
    """Demo the tailoring functionality"""
    # NOTE: RESUME_DATA here is a mock based on your new resume structure.
    # In main.py, it should be loaded from the structured profile file.
    
    # Update RESUME_DATA with the actual achievements/projects structure from your resume text
    mock_resume_data = RESUME_DATA.copy()
    mock_resume_data["projects"] = [
        {"name": "AI-Powered Triage & Classification Engine (Proof of Concept)", "dates": "Nov 2025 – Present", "details": "Architected a Python-based automation solution designed to modernize high-volume Service Desk operations", "achievements": ["Automated Tier 1 ticket classification, aiming to reduce manual triage time by 40%", "Aligned with ISO/IEC 42001 transparency principles, including PII safeguards and audit logging", "Modular routing system with assertion-based validation testing"]},
    ]
    mock_resume_data["experience"][0]["achievements"] = [
        "Directed support operations for ~150 dealer partners across CAD/CAM and SaaS ecosystems", 
        "Led a 10-person support unit, achieving 99% uptime and aggressive SLA compliance", 
        "Built 'MillBox 101' onboarding and centralized SOP library, reducing onboarding time by 50%", 
        "Presented technical strategy sessions at Lab Day West (2023–2024) to 100+ professionals"
    ]
    
    
    # Mock AI_CONFIG and OUTPUT_PATH for local demo run if they aren't available
    global AI_CONFIG, OUTPUT_PATH
    if AI_CONFIG["api_key"] == "YOUR_API_KEY":
        print("\n--- WARNING: AI_CONFIG API KEY NOT SET. SKIPPING LIVE DEMO. ---\n")
        return

    tailor = ResumeTailor(mock_resume_data)
    
    sample_job = """
    Senior AI Governance and Service Desk Automation Strategist
    Enterprise Solutions Group (ESG)
    
    We are seeking a senior strategist with deep experience in IT operations modernization, focusing on Responsible AI governance.
    
    Key Responsibilities:
    - Establish and maintain AI Governance Frameworks compliant with ISO/IEC 42001.
    - Design and implement Generative AI solutions for high-volume Service Desk automation (ticket triage, self-service).
    - Lead risk management activities related to PII and model transparency.
    - Mentor junior analysts and report on key operational KPIs.
    
    Requirements:
    - 10+ years in IT Strategy or Operations.
    - Proven expertise in Python for automation and workflow analysis.
    - Strong background in SLA optimization and technical training.
    """
    
    result = tailor.generate_tailored_resume(sample_job)
    
    if result.success:
        print("✅ Tailored resume generated successfully!")
        print(f"File saved: {result.file_path}")
        print(f"Total tokens used: {result.tokens_used}")
        print(f"Sections generated: {result.sections_generated}")
        print("\n--- Sample Output Summary ---")
        print(result.tailored_content.split('## CORE COMPETENCIES')[0])
    else:
        print(f"❌ Failed: {result.error}")


if __name__ == "__main__":
    demo_tailoring()

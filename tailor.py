"""
Resume tailoring engine - Generates tailored resumes using AI.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib

import tiktoken
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

from config.settings import RESUME_DATA, AI_CONFIG, TAILORING, OUTPUT_PATH

logger = logging.getLogger(__name__)


@dataclass
class TailoringResult:
    """Result of resume tailoring operation"""
    success: bool
    tailored_content: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int = 0
    sections_generated: int = 0


class ResumeSection:
    """Represents a section of the resume"""
    def __init__(self, name: str, content: str, weight: float = 1.0):
        self.name = name
        self.content = content
        self.weight = weight
        self.is_generated = False
        self.tokens_used = 0


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
        
        # ✅ PYINSTALLER FIX: Try normal path first, fallback to explicit registration
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # For token counting
        except ValueError:
            # Fallback for PyInstaller bundles - load encoding directly
            logger.warning("tiktoken encoding not found via normal path, using fallback")
            import tiktoken_ext.openai_public
            tiktoken.registry.ENCODINGS["cl100k_base"] = tiktoken_ext.openai_public.cl100k_base
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        self.model_name = AI_CONFIG["model"]
        logger.info("✓ ResumeTailor initialized with AI model")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, estimating")
            # Fallback estimation: ~1 token per 4 characters
            return len(text) // 4

    def extract_keywords(self, text: str) -> List[str]:
        """Extract key skills and terms from job description"""
        # Tech skills pattern
        tech_pattern = r'\b(?:Python|JavaScript|SQL|AWS|Azure|Docker|Kubernetes|CI/CD|Git|React|Node\.js|API|REST|GraphQL|Machine Learning|AI|Cloud|Infrastructure|Security|Networking|Linux|Windows|Active Directory|VPN|Firewall|SAML|OAuth)\b'
        
        # Experience level
        exp_pattern = r'\b(?:senior|lead|principal|staff|architect|manager|director|junior|entry|mid-level)\b'
        
        # Combine patterns
        keywords = []
        
        # Tech skills
        tech_matches = re.findall(tech_pattern, text, re.IGNORECASE)
        keywords.extend([match.lower() for match in tech_matches])
        
        # Experience indicators
        exp_matches = re.findall(exp_pattern, text, re.IGNORECASE)
        keywords.extend([match.lower() for match in exp_matches])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        logger.info(f"✓ Extracted {len(unique_keywords)} keywords from job description")
        return unique_keywords

    def analyze_job_description(self, job_text: str) -> Dict[str, Any]:
        """Analyze job description and extract key requirements"""
        prompt = f"""
        Analyze this job description and provide a structured analysis:
        
        Job Description:
        {job_text}
        
        Provide your analysis in the following format:
        1. Primary role/title
        2. Required technical skills (list)
        3. Experience level (junior/mid/senior)
        4. Key responsibilities (list)
        5. Industry/sector
        6. Special requirements or preferences
        
        Format as structured data that can be parsed.
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
            
            analysis = response.text
            logger.info("✓ Job description analysis completed")
            return {"raw_analysis": analysis}
            
        except Exception as e:
            logger.error(f"Job analysis failed: {e}")
            return {"error": str(e)}

    def generate_summary(self, job_analysis: Dict[str, Any]) -> str:
        """Generate a customized professional summary"""
        base_summary = self.resume.get("summary", "")
        
        prompt = f"""
        Generate a compelling professional summary (3-4 sentences) that:
        1. Aligns with this job analysis
        2. Highlights relevant experience from the base resume
        3. Uses strong action verbs and quantifies achievements where possible
        4. Incorporates key skills and technologies
        
        Base Resume Summary:
        {base_summary}
        
        Job Analysis:
        {job_analysis.get('raw_analysis', '')}
        
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
            logger.info("✓ Generated customized summary")
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return base_summary  # Fallback to base summary

    def tailor_experience(self, job_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Tailor experience section to highlight relevant roles and achievements"""
        relevant_experience = []
        
        for exp in self.resume.get("experience", []):
            # Calculate relevance score based on keywords and skills
            relevance_score = self._calculate_experience_relevance(exp, job_analysis)
            
            if relevance_score > 0.3:  # Include moderately relevant experience
                tailored_exp = {
                    "title": exp["title"],
                    "company": exp["company"],
                    "dates": exp["dates"],
                    "location": exp.get("location", ""),
                    "relevance_score": relevance_score
                }
                
                # Generate tailored achievements for this role
                if "achievements" in exp:
                    tailored_exp["achievements"] = self._tailor_achievements(
                        exp["achievements"], job_analysis
                    )
                
                relevant_experience.append(tailored_exp)
        
        # Sort by relevance score (descending)
        relevant_experience.sort(key=lambda x: x["relevance_score"], reverse=True)
        logger.info(f"✓ Tailored {len(relevant_experience)} experience entries")
        return relevant_experience

    def _calculate_experience_relevance(self, exp: Dict, job_analysis: Dict) -> float:
        """Calculate relevance score for an experience entry"""
        score = 0.0
        job_text = job_analysis.get('raw_analysis', '').lower()
        
        # Title relevance
        if exp["title"].lower() in job_text:
            score += 0.4
        
        # Skills used
        skills_used = exp.get("skills_used", [])
        for skill in skills_used:
            if skill.lower() in job_text:
                score += 0.1
        
        # Company type relevance (tech companies score higher for tech roles)
        if any(keyword in job_text for keyword in ["tech", "software", "saas", "startup"]):
            if "tech" in exp.get("company", "").lower():
                score += 0.2
        
        # Cap at 1.0
        return min(score, 1.0)

    def _tailor_achievements(self, achievements: List[str], job_analysis: Dict) -> List[str]:
        """Tailor achievements to be more relevant to the job"""
        job_text = job_analysis.get('raw_analysis', '').lower()
        tailored_achievements = []
        
        for achievement in achievements:
            # If achievement mentions skills or results relevant to job, prioritize it
            achievement_lower = achievement.lower()
            
            # Check for relevant keywords
            has_relevant_keywords = any(
                keyword in achievement_lower 
                for keyword in job_text.split()
            )
            
            # Check for quantified results (numbers are always good)
            has_quantified_results = any(char.isdigit() for char in achievement)
            
            if has_relevant_keywords or has_quantified_results:
                tailored_achievements.append(achievement)
        
        # If no achievements matched, include the best ones anyway
        if not tailored_achievements and achievements:
            tailored_achievements = achievements[:2]  # Top 2 achievements
        
        return tailored_achievements

    def generate_technical_skills(self, job_analysis: Dict[str, Any]) -> List[str]:
        """Generate a tailored technical skills section"""
        job_keywords = set()
        
        # Extract skills from job analysis
        analysis_text = job_analysis.get('raw_analysis', '').lower()
        
        # Match with resume skills
        resume_skills = []
        for category, skills in self.resume.get("skills", {}).items():
            resume_skills.extend(skills)
        
        # Prioritize skills mentioned in job description
        prioritized_skills = []
        for skill in resume_skills:
            if skill.lower() in analysis_text:
                prioritized_skills.append(skill)
        
        # Add other relevant skills
        remaining_skills = [s for s in resume_skills if s not in prioritized_skills]
        prioritized_skills.extend(remaining_skills[:10])  # Max 10-15 skills
        
        logger.info(f"✓ Generated tailored skills list ({len(prioritized_skills)} skills)")
        return prioritized_skills[:15]  # Limit to top 15 skills

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
        
        try:
            # Step 1: Analyze job description
            logger.info("📋 Analyzing job description...")
            job_analysis = self.analyze_job_description(job_description)
            
            if "error" in job_analysis:
                return TailoringResult(
                    success=False,
                    error=f"Job analysis failed: {job_analysis['error']}"
                )
            
            # Step 2: Generate tailored sections
            logger.info("✨ Generating tailored sections...")
            
            sections = {}
            
            # Professional Summary
            sections["summary"] = self.generate_summary(job_analysis)
            
            # Technical Skills
            sections["skills"] = self.generate_technical_skills(job_analysis)
            
            # Experience
            sections["experience"] = self.tailor_experience(job_analysis)
            
            # Education (keep as-is)
            sections["education"] = self.resume.get("education", [])
            
            # Certifications (keep as-is)
            sections["certifications"] = self.resume.get("certifications", [])
            
            # Step 3: Compile final resume
            logger.info("📄 Compiling final resume...")
            if output_format == "markdown":
                resume_content = self._compile_markdown_resume(sections)
            else:
                resume_content = self._compile_text_resume(sections)
            
            # Step 4: Count tokens and save
            tokens_used = self.count_tokens(resume_content)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_hash = hashlib.md5(job_description[:100].encode()).hexdigest()[:8]
            filename = f"tailored_resume_{timestamp}_{file_hash}.md"
            file_path = OUTPUT_PATH / filename
            
            # Save file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(resume_content)
            
            logger.info(f"✅ Resume tailoring completed: {file_path}")
            return TailoringResult(
                success=True,
                tailored_content=resume_content,
                file_path=str(file_path),
                tokens_used=tokens_used,
                sections_generated=len(sections)
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
        
        # Header
        content.append(f"# {self.resume.get('name', 'Professional Resume')}")
        content.append(f"**{self.resume.get('title', 'Experienced Professional')}**")
        content.append("")
        
        # Contact info (if available)
        if "contact" in self.resume:
            contact = self.resume["contact"]
            contact_line = " | ".join([
                contact.get("email", ""),
                contact.get("phone", ""),
                contact.get("location", "")
            ]).strip(" | ")
            if contact_line:
                content.append(contact_line)
                content.append("")
        
        # Summary
        content.append("## Professional Summary")
        content.append(sections["summary"])
        content.append("")
        
        # Technical Skills
        content.append("## Technical Skills")
        skills_text = " | ".join(sections["skills"])
        content.append(skills_text)
        content.append("")
        
        # Experience
        content.append("## Professional Experience")
        for exp in sections["experience"]:
            content.append(f"### {exp['title']}")
            content.append(f"**{exp['company']}** | {exp['dates']}")
            if exp.get("location"):
                content.append(f"*{exp['location']}*")
            
            if "achievements" in exp:
                for achievement in exp["achievements"]:
                    content.append(f"- {achievement}")
            content.append("")
        
        # Education
        if sections["education"]:
            content.append("## Education")
            for edu in sections["education"]:
                content.append(f"- {edu.get('degree', '')} - {edu.get('school', '')}")
            content.append("")
        
        # Certifications
        if sections["certifications"]:
            content.append("## Certifications")
            for cert in sections["certifications"]:
                content.append(f"- {cert}")
        
        return "\n".join(content)

    def _compile_text_resume(self, sections: Dict[str, Any]) -> str:
        """Compile sections into plain text format"""
        # Similar to markdown but simpler formatting
        # Implementation omitted for brevity, falls back to markdown
        return self._compile_markdown_resume(sections)


def demo_tailoring():
    """Demo the tailoring functionality"""
    tailor = ResumeTailor(RESUME_DATA)
    
    sample_job = """
    Senior AI Infrastructure Engineer
    TechCorp Solutions
    
    We are seeking a senior-level engineer with expertise in:
    - AWS cloud infrastructure and architecture
    - Python and automation
    - Machine learning operations (MLOps)
    - Security and governance frameworks
    - Team leadership and training
    
    Requirements:
    - 5+ years in infrastructure engineering
    - Experience with AI/ML pipeline deployment
    - Strong understanding of cybersecurity principles
    """
    
    result = tailor.generate_tailored_resume(sample_job)
    
    if result.success:
        print("✅ Tailored resume generated successfully!")
        print(f"File saved: {result.file_path}")
        print(f"Tokens used: {result.tokens_used}")
        print(f"Sections generated: {result.sections_generated}")
    else:
        print(f"❌ Failed: {result.error}")


if __name__ == "__main__":
    demo_tailoring()

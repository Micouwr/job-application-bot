"""
Resume and cover letter tailoring with AI
"""
import logging
from typing import Dict, List, Tuple
from anthropic import Anthropic
from config.settings import ANTHROPIC_API_KEY, RESUME_DATA, TAILORING

logger = logging.getLogger(__name__)


class ResumeTailor:
    """AI-powered resume and cover letter tailoring"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Set it in .env file")
        
        self.client = Anthropic(api_key=self.api_key)
        self.resume_data = RESUME_DATA
    
    def tailor_application(self, job: Dict, match_result: Dict) -> Dict:
        """
        Create complete tailored application
        Returns: {resume_text, cover_letter, changes}
        """
        logger.info(f"Tailoring application for {job['title']} at {job['company']}")
        
        # Generate tailored resume
        resume_text, changes = self._tailor_resume(job, match_result)
        
        # Generate cover letter
        cover_letter = self._generate_cover_letter(job, match_result)
        
        return {
            'resume_text': resume_text,
            'cover_letter': cover_letter,
            'changes': changes
        }
    
    def _tailor_resume(self, job: Dict, match: Dict) -> Tuple[str, List[str]]:
        """Tailor resume for specific job"""
        
        prompt = f"""You are tailoring a resume for a specific job application.

CRITICAL RULES:
1. Do NOT add any experience, skills, or achievements not in the original resume
2. Do NOT change dates, companies, or job titles
3. ONLY reorder content and adjust emphasis
4. Keep all information factual and truthful

RESUME DATA:
{self._format_resume_for_prompt()}

TARGET JOB:
Title: {job['title']}
Company: {job['company']}
Description: {job.get('description', '')[:800]}

MATCH ANALYSIS:
- Match Score: {match['match_score']*100:.1f}%
- Matched Skills: {', '.join(match['matched_skills'])}
- Relevant Experience: {'; '.join(match['relevant_experience'][:2])}

TASK:
Create a tailored resume that:
1. Adjusts professional summary to emphasize most relevant skills
2. Reorders experience bullets to highlight relevant achievements first
3. Prioritizes matching skills in skills section
4. Maintains exact dates, titles, and companies

Format as a clean, professional resume. Return ONLY the resume text."""

        try:
            response = self.client.messages.create(
                model=TAILORING['model'],
                max_tokens=TAILORING['max_tokens'],
                messages=[{"role": "user", "content": prompt}]
            )
            
            resume_text = response.content[0].text
            
            # Track changes
            changes = [
                "Adjusted professional summary for relevance",
                f"Emphasized {len(match['matched_skills'])} matching skills",
                "Reordered experience bullets"
            ]
            
            logger.info("Resume tailored successfully")
            return resume_text, changes
            
        except Exception as e:
            logger.error(f"Error tailoring resume: {e}")
            # Fallback to original resume
            return self._format_original_resume(), ["No changes - using original resume"]
    
    def _generate_cover_letter(self, job: Dict, match: Dict) -> str:
        """Generate tailored cover letter"""
        
        prompt = f"""Write a professional cover letter for this job application.

CANDIDATE INFO:
{self._format_resume_for_prompt()}

JOB:
Title: {job['title']}
Company: {job['company']}
Description: {job.get('description', '')[:600]}

MATCH STRENGTHS:
{'; '.join(match['strengths'])}

REQUIREMENTS:
- 3 paragraphs, 250-350 words
- Professional but personable tone
- Opening: Express interest in role
- Body: Highlight 2-3 specific relevant experiences with examples
- Closing: Express enthusiasm and availability
- Do NOT use clichés like "perfect fit"
- Do NOT mention skills not in resume

Write the cover letter now:"""

        try:
            response = self.client.messages.create(
                model=TAILORING['model'],
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            cover_letter = response.content[0].text
            logger.info("Cover letter generated successfully")
            return cover_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            return self._template_cover_letter(job, match)
    
    def _format_resume_for_prompt(self) -> str:
        """Format resume data for AI prompt"""
        resume = self.resume_data
        
        text = f"""Name: {resume['personal']['name']}
Title: {resume['personal']['title']}
Location: {resume['personal']['location']}
Email: {resume['personal']['email']}
Phone: {resume['personal']['phone']}

SUMMARY:
{resume['summary']}

SKILLS:
"""
        for category, skills in resume['skills'].items():
            text += f"- {category.replace('_', ' ').title()}: {', '.join(skills)}\n"
        
        text += "\nEXPERIENCE:\n"
        for exp in resume['experience']:
            text += f"\n{exp['title']} | {exp['company']} | {exp['dates']}\n"
            for achievement in exp['achievements']:
                text += f"  • {achievement}\n"
        
        text += "\nPROJECTS:\n"
        for proj in resume.get('projects', []):
            text += f"\n{proj['name']} | {proj['dates']}\n"
            text += f"{proj['description']}\n"
        
        text += "\nCERTIFICATIONS:\n"
        for cert in resume['certifications']:
            text += f"  • {cert['name']} - {cert['issuer']}\n"
        
        return text
    
    def _format_original_resume(self) -> str:
        """Format original resume as text"""
        resume = self.resume_data
        
        lines = []
        lines.append(f"{resume['personal']['name'].upper()}")
        lines.append(f"{resume['personal']['title']}")
        lines.append(f"{resume['personal']['location']} | {resume['personal']['phone']} | {resume['personal']['email']}")
        lines.append("")
        
        lines.append("PROFESSIONAL SUMMARY")
        lines.append("-" * 80)
        lines.append(resume['summary'])
        lines.append("")
        
        lines.append("CORE COMPETENCIES")
        lines.append("-" * 80)
        for category, skills in resume['skills'].items():
            lines.append(f"• {category.replace('_', ' ').title()}: {', '.join(skills)}")
        lines.append("")
        
        lines.append("PROFESSIONAL EXPERIENCE")
        lines.append("-" * 80)
        for exp in resume['experience']:
            lines.append(f"{exp['title']} | {exp['company']} | {exp['dates']}")
            for ach in exp['achievements']:
                lines.append(f"  • {ach}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _template_cover_letter(self, job: Dict, match: Dict) -> str:
        """Fallback template cover letter"""
        return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job['title']} position at {job['company']}. With over 20 years of IT infrastructure experience and recent certifications in AI governance, I believe I can contribute significantly to your team.

In my recent role as Digital Dental Technical Specialist at CIMSystem, I led a 10-person help desk supporting 150 dealer partners, achieving 90% first-contact resolution and reducing time-to-first-mill by 50%. This experience in technical leadership and enablement aligns well with the requirements outlined in your job description.

My expertise in {', '.join(match['matched_skills'][:3])} has been central to my career success. I'm particularly excited about applying my AI governance knowledge and ISO/IEC 42001 certification to help {job['company']} navigate the evolving landscape of responsible AI implementation.

I would welcome the opportunity to discuss how my experience can benefit your team. Thank you for your consideration.

Best regards,
{self.resume_data['personal']['name']}
{self.resume_data['personal']['phone']}
{self.resume_data['personal']['email']}"""


def demo_tailor():
    """Demo the tailor"""
    from scraper import demo_scraper
    from matcher import JobMatcher
    
    # Get sample job
    jobs = demo_scraper()
    job = jobs[0]
    
    # Match it
    matcher = JobMatcher()
    match = matcher.match_job(job)
    
    # Tailor application
    tailor = ResumeTailor()
    application = tailor.tailor_application(job, match)
    
    print("\n=== TAILORED APPLICATION ===\n")
    print("RESUME:")
    print(application['resume_text'][:500] + "...")
    print("\n" + "="*80 + "\n")
    print("COVER LETTER:")
    print(application['cover_letter'])
    print("\n" + "="*80 + "\n")
    print("CHANGES MADE:")
    for change in application['changes']:
        print(f"  • {change}")


if __name__ == "__main__":
    demo_tailor()

"""
Resume tailoring engine - Generates customized narratives for job applications
"""
from typing import Dict, List


class ResumeTailor:
    """Tailor resume narratives for specific job applications"""

    def __init__(self, resume: Dict):
        self.resume = resume

    def generate_analysis(self, match: Dict, job: Dict) -> List[str]:
        """Generate narrative analysis for a given match result"""
        analysis = [
            f"- Match Score: {match['match_score']*100:.1f}%",
            f"- Matched Skills: {', '.join(match['matched_skills'])}",
            f"- Relevant Experience: {'; '.join(match['relevant_experience'][:2])}"
        ]
        return analysis

    def generate_narrative(self, match: Dict, job: Dict) -> str:
        """Generate a tailored narrative paragraph for a job application"""
        narrative = (
            f"My expertise in {', '.join(match['matched_skills'][:3])} "
            f"has been central to my career success. I'm particularly excited "
            f"about applying my AI governance knowledge and ISO/IEC 42001 certification "
            f"to help {job['company']} navigate the evolving landscape of responsible AI implementation."
        )
        return narrative


# Demo usage
if __name__ == "__main__":
    # Example resume and job data
    resume = {
        "skills": {"technical": ["Python", "AI Governance", "ISO/IEC 42001"]},
        "experience": [
            {"title": "AI Specialist", "company": "TechCorp", "dates": "2020-2023",
             "skills_used": ["Python", "AI Governance"], "achievements": ["Implemented ISO/IEC 42001"]}
        ]
    }

    job = {"id": 1, "title": "AI Governance Lead", "company": "FutureAI"}

    match = {
        "match_score": 0.87,
        "matched_skills": ["Python", "AI Governance", "ISO/IEC 42001"],
        "relevant_experience": ["AI Specialist at TechCorp (2020-2023)"]
    }

    tailor = ResumeTailor(resume)
    print("\n=== MATCH ANALYSIS ===")
    for line in tailor.generate_analysis(match, job):
        print(line)

    print("\n=== NARRATIVE ===")
    print(tailor.generate_narrative(match, job))

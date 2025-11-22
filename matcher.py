"""
Job matching engine - Scores jobs against resume
"""
import logging
from typing import Dict, List, Tuple
from config.settings import RESUME_DATA, MATCHING

logger = logging.getLogger(__name__)


class JobMatcher:
    """Match jobs against resume"""
    
    def __init__(self, resume_data: Dict = None):
        self.resume = resume_data or RESUME_DATA
        self.all_skills = self._extract_all_skills()
        self.experience_keywords = self._extract_experience_keywords()
    
    def _extract_all_skills(self) -> set:
        """Extract all skills from resume"""
        skills = set()
        for category in self.resume['skills'].values():
            skills.update([s.lower() for s in category])
        return skills
    
    def _extract_experience_keywords(self) -> set:
        """Extract keywords from experience"""
        keywords = set()
        for exp in self.resume['experience']:
            for skill in exp.get('skills_used', []):
                keywords.add(skill.lower())
            # Add key terms from achievements
            for achievement in exp.get('achievements', []):
                keywords.update(achievement.lower().split())
        return keywords
    
    def match_job(self, job: Dict) -> Dict:
        """
        Calculate comprehensive match score
        Returns match result with score and analysis
        """
        job_text = f"{job['title']} {job.get('description', '')} {job.get('requirements', '')}".lower()
        
        # 1. Skills matching (40%)
        skills_score, matched_skills, missing_skills = self._calculate_skills_match(job_text)
        
        # 2. Experience relevance (40%)
        experience_score, relevant_exp = self._calculate_experience_match(job_text)
        
        # 3. Keyword match (20%)
        keyword_score, keyword_matches = self._calculate_keyword_match(job_text)
        
        # Calculate weighted score
        base_score = (
            MATCHING['weights']['skills'] * skills_score +
            MATCHING['weights']['experience'] * experience_score +
            MATCHING['weights']['keywords'] * keyword_score
        )
        
        # Experience level adjustment
        exp_match = self._check_experience_level(job)
        multiplier = 1.0 if exp_match else MATCHING['experience_level_multiplier']
        
        match_score = base_score * multiplier
        
        # Generate analysis
        strengths, gaps = self._analyze_fit(matched_skills, missing_skills, relevant_exp)
        reasoning = self._generate_reasoning(
            match_score, skills_score, experience_score,
            matched_skills, missing_skills, relevant_exp
        )
        
        # Recommendation
        if match_score >= 0.85:
            recommendation = "STRONG FIT - Highly recommended"
        elif match_score >= 0.80:
            recommendation = "GOOD FIT - Recommended"
        elif match_score >= 0.70:
            recommendation = "MODERATE FIT - Review manually"
        else:
            recommendation = "SKIP - Not a strong match"
        
        return {
            'job_id': job['id'],
            'match_score': round(match_score, 3),
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'relevant_experience': relevant_exp,
            'keyword_matches': keyword_matches,
            'strengths': strengths,
            'gaps': gaps,
            'recommendation': recommendation,
            'reasoning': reasoning,
            'scores': {
                'skills': skills_score,
                'experience': experience_score,
                'keywords': keyword_score
            }
        }
    
    def _calculate_skills_match(self, job_text: str) -> Tuple[float, List[str], List[str]]:
        """Calculate skills match score"""
        # Define skill keywords to look for
        skill_patterns = {
            'ai governance': ['ai governance', 'ai management', 'responsible ai'],
            'iso 42001': ['iso/iec 42001', 'iso 42001', 'ai standard'],
            'aws': ['aws', 'amazon web services'],
            'help desk': ['help desk', 'service desk', 'technical support'],
            'active directory': ['active directory', 'ad', 'ldap'],
            'cisco': ['cisco', 'meraki'],
            'vpn': ['vpn', 'virtual private network'],
            'python': ['python'],
            'linux': ['linux', 'unix'],
            'networking': ['network', 'networking', 'tcp/ip'],
            'security': ['security', 'cybersecurity'],
            'training': ['training', 'enablement', 'onboarding'],
            'sla': ['sla', 'service level'],
            'cloud': ['cloud', 'cloud infrastructure']
        }
        
        matched = []
        for skill, patterns in skill_patterns.items():
            if any(pattern in job_text for pattern in patterns):
                if any(skill.lower() in resume_skill or resume_skill in skill.lower() 
                       for resume_skill in self.all_skills):
                    matched.append(skill.title())
        
        # Find mentioned but not matched skills
        missing = []
        for skill, patterns in skill_patterns.items():
            if any(pattern in job_text for pattern in patterns):
                if skill.title() not in matched:
                    missing.append(skill.title())
        
        # Score based on matches vs requirements
        total_required = len(matched) + len(missing)
        score = len(matched) / total_required if total_required > 0 else 1.0
        
        return score, matched, missing
    
    def _calculate_experience_match(self, job_text: str) -> Tuple[float, List[str]]:
        """Calculate experience relevance"""
        relevant_exp = []
        
        for exp in self.resume['experience']:
            relevance = 0
            
            # Check role keywords
            if exp['title'].lower() in job_text:
                relevance += 0.3
            
            # Check skills used
            for skill in exp.get('skills_used', []):
                if skill.lower() in job_text:
                    relevance += 0.1
            
            if relevance > 0.2:
                relevant_exp.append(
                    f"{exp['title']} at {exp['company']} ({exp['dates']})"
                )
        
        # Score based on relevant experiences
        score = min(len(relevant_exp) / 2.0, 1.0)
        
        return score, relevant_exp
    
    def _calculate_keyword_match(self, job_text: str) -> Tuple[float, Dict[str, int]]:
        """Calculate keyword matches"""
        keywords = {
            'help desk': 0, 'service desk': 0, 'infrastructure': 0,
            'architect': 0, 'cloud': 0, 'ai': 0, 'governance': 0,
            'training': 0, 'leadership': 0, 'senior': 0, 'manager': 0
        }
        
        for keyword in keywords:
            keywords[keyword] = job_text.count(keyword)
        
        matched = sum(1 for count in keywords.values() if count > 0)
        score = matched / len(keywords)
        
        return score, {k: v for k, v in keywords.items() if v > 0}
    
    def _check_experience_level(self, job: Dict) -> bool:
        """Check if experience level matches"""
        title = job['title'].lower()
        exp_level = job.get('experience_level', '').lower()
        
        senior_indicators = ['senior', 'sr.', 'lead', 'principal', 'architect', 'manager']
        return any(indicator in title or indicator in exp_level for indicator in senior_indicators)
    
    def _analyze_fit(self, matched: List[str], missing: List[str], 
                     relevant_exp: List[str]) -> Tuple[List[str], List[str]]:
        """Analyze strengths and gaps"""
        strengths = []
        gaps = []
        
        if len(matched) >= 5:
            strengths.append(f"Strong skill alignment ({len(matched)} matched skills)")
        
        if len(relevant_exp) >= 2:
            strengths.append(f"Relevant experience ({len(relevant_exp)} positions)")
        
        if any('ai' in s.lower() or 'governance' in s.lower() for s in matched):
            strengths.append("AI/Governance expertise aligns with emerging needs")
        
        if missing and len(missing) > len(matched):
            gaps.append(f"Missing {len(missing)} requested skills")
        
        return strengths, gaps
    
    def _generate_reasoning(self, score: float, skills: float, exp: float,
                           matched: List[str], missing: List[str], 
                           relevant: List[str]) -> str:
        """Generate reasoning"""
        parts = [
            f"Overall: {score*100:.1f}%",
            f"Skills: {skills*100:.1f}%",
            f"Experience: {exp*100:.1f}%"
        ]
        
        if matched:
            parts.append(f"Matched: {', '.join(matched[:3])}")
        
        if missing:
            parts.append(f"Missing: {', '.join(missing[:2])}")
        
        return " | ".join(parts)


def demo_matcher():
    """Demo the matcher"""
    from scraper import demo_scraper
    
    # Get sample jobs
    jobs = demo_scraper()
    
    # Match them
    matcher = JobMatcher()
    
    print("\n=== MATCHING RESULTS ===\n")
    for job in jobs:
        result = matcher.match_job(job)
        print(f"Job: {job['title']} at {job['company']}")
        print(f"Match Score: {result['match_score']*100:.1f}%")
        print(f"Recommendation: {result['recommendation']}")
        print(f"Matched Skills: {', '.join(result['matched_skills'][:5])}")
        print(f"Reasoning: {result['reasoning']}")
        print("-" * 80)


if __name__ == "__main__":
    demo_matcher()

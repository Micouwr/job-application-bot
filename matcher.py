"""
Job matching engine - Scores jobs against resume
Improved with type safety, better algorithms, and performance.
"""

import logging
import re
from typing import Dict, List, Tuple, Set, Any, Optional

from config.settings import Config

logger = logging.getLogger(__name__)

class JobMatcher:
    """Match jobs against resume with improved algorithms"""
    
    def __init__(self, resume_data: Optional[Dict[str, Any]] = None):
        self.resume: Dict[str, Any] = resume_data or Config.RESUME_DATA
        self.all_skills: Set[str] = self._extract_all_skills()
        self.experience_keywords: Set[str] = self._extract_experience_keywords()
        self.job_keywords: Set[str] = self._build_job_keywords()
    
    def _extract_all_skills(self) -> Set[str]:
        """Extract all skills from resume, normalized"""
        skills = set()
        try:
            for category in self.resume.get("skills", {}).values():
                if isinstance(category, list):
                    skills.update(s.lower().strip() for s in category if s)
        except Exception as e:
            logger.warning(f"Error extracting skills: {e}")
        return skills
    
    def _extract_experience_keywords(self) -> Set[str]:
        """Extract keywords from experience section"""
        keywords = set()
        try:
            for exp in self.resume.get("experience", []):
                # Add skills used
                for skill in exp.get("skills_used", []):
                    if skill:
                        keywords.add(skill.lower().strip())
                
                # Add key terms from achievements
                for achievement in exp.get("achievements", []):
                    if achievement:
                        # Extract words (3+ chars, not common stopwords)
                        words = re.findall(r'\b[a-z]{3,}\b', achievement.lower())
                        stopwords = {'the', 'and', 'for', 'with', 'was', 'has', 'had', 'that', 'this'}
                        keywords.update(w for w in words if w not in stopwords)
        except Exception as e:
            logger.warning(f"Error extracting experience keywords: {e}")
        return keywords
    
    def _build_job_keywords(self) -> Set[str]:
        """Build set of typical job search keywords"""
        try:
            keywords = set(Config.RESUME_DATA.get("skills", {}).keys())
            # Add common IT job terms
            keywords.update([
                "help desk", "service desk", "infrastructure", "architect", "cloud",
                "ai", "governance", "training", "leadership", "senior", "manager",
                "network", "security", "python", "linux"
            ])
            return {k.lower() for k in keywords if k}
        except Exception as e:
            logger.warning(f"Error building job keywords: {e}")
            return set()
    
    def match_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive match score with detailed analysis.
        Improved accuracy and performance.
        """
        try:
            # Combine all job text for matching
            job_text = " ".join([
                job.get('title', ''),
                job.get('description', ''),
                job.get('requirements', ''),
                job.get('company', '')
            ]).lower()
            
            if not job_text.strip():
                logger.warning(f"Empty job text for job: {job.get('title', 'Unknown')}")
                return self._build_empty_match(job["id"])
            
            # 1. Skills matching (40% weight)
            skills_score, matched_skills, missing_skills = self._calculate_skills_match(job_text)
            
            # 2. Experience relevance (40% weight)
            experience_score, relevant_exp = self._calculate_experience_match(job_text)
            
            # 3. Keyword match (20% weight)
            keyword_score, keyword_matches = self._calculate_keyword_match(job_text)
            
            # Calculate weighted base score
            weights = Config.MATCHING_WEIGHTS
            base_score = (
                weights["skills"] * skills_score +
                weights["experience"] * experience_score +
                weights["keywords"] * keyword_score
            )
            
            # Experience level adjustment
            exp_match = self._check_experience_level(job)
            multiplier = 1.0 if exp_match else Config.MATCHING.get("experience_level_multiplier", 0.85)
            
            match_score = min(base_score * multiplier, 1.0)
            
            # Generate comprehensive analysis
            strengths, gaps = self._analyze_fit(
                matched_skills, missing_skills, relevant_exp
            )
            
            reasoning = self._generate_reasoning(
                match_score, skills_score, experience_score,
                matched_skills, missing_skills, relevant_exp
            )
            
            recommendation = self._get_recommendation(match_score)
            
            return {
                "job_id": job["id"],
                "match_score": round(match_score, 3),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "relevant_experience": relevant_exp,
                "keyword_matches": keyword_matches,
                "strengths": strengths,
                "gaps": gaps,
                "recommendation": recommendation,
                "reasoning": reasoning,
                "scores": {
                    "skills": round(skills_score, 3),
                    "experience": round(experience_score, 3),
                    "keywords": round(keyword_score, 3),
                },
                "metadata": {
                    "experience_level_match": exp_match,
                    "total_skills_checked": len(self.all_skills),
                }
            }
            
        except Exception as e:
            logger.error(f"Error matching job {job.get('id', 'unknown')}: {e}")
            return self._build_empty_match(job.get("id", "unknown"))
    
    def _build_empty_match(self, job_id: str) -> Dict[str, Any]:
        """Return empty match result for error cases"""
        return {
            "job_id": job_id,
            "match_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "relevant_experience": [],
            "keyword_matches": {},
            "strengths": [],
            "gaps": ["Error during matching"],
            "recommendation": "SKIP - Error in matching",
            "reasoning": "Failed to analyze job",
            "scores": {"skills": 0.0, "experience": 0.0, "keywords": 0.0},
            "metadata": {"experience_level_match": False, "total_skills_checked": 0},
        }
    
    def _calculate_skills_match(self, job_text: str) -> Tuple[float, List[str], List[str]]:
        """Calculate skills match with partial matching support"""
        try:
            if not self.all_skills:
                return 0.0, [], []
            
            matched_skills = []
            missing_skills = []
            
            for skill in self.all_skills:
                # Check for exact match or skill as substring of job text
                # e.g., "python" matches "python 3.x"
                if skill in job_text:
                    matched_skills.append(skill)
                # Also check reverse: job requirement might be "python scripting" but skill is "python"
                elif any(skill_part in job_text for skill_part in skill.split()):
                    matched_skills.append(skill)
                else:
                    missing_skills.append(skill)
            
            # Calculate score with smoothing to avoid perfect match requirement
            score = len(matched_skills) / len(self.all_skills) if self.all_skills else 0.0
            
            # Return formatted skill names
            return (
                score,
                [s.title() for s in matched_skills],
                [s.title() for s in missing_skills],
            )
        except Exception as e:
            logger.warning(f"Error in skills matching: {e}")
            return 0.0, [], []
    
    def _calculate_experience_match(self, job_text: str) -> Tuple[float, List[str]]:
        """Calculate experience relevance with weighted scoring"""
        try:
            relevant_exp = []
            total_relevance = 0.0
            
            for exp in self.resume.get("experience", []):
                relevance = 0.0
                
                # Title match (high weight)
                title = exp.get("title", "").lower()
                if title and title in job_text:
                    relevance += 0.5
                
                # Company match (lower weight)
                company = exp.get("company", "").lower()
                if company and company in job_text:
                    relevance += 0.2
                
                # Skills used match
                for skill in exp.get("skills_used", []):
                    if skill and skill.lower() in job_text:
                        relevance += 0.1
                
                # If relevance threshold met, add to list
                if relevance >= 0.3:
                    years = exp.get("dates", "")
                    relevant_exp.append(f"{exp.get('title', '')} at {exp.get('company', '')} ({years})")
                    total_relevance += relevance
            
            # Normalize score
            score = min(total_relevance / 2.0, 1.0)  # 2.0 = threshold for "good" match
            
            return score, relevant_exp
            
        except Exception as e:
            logger.warning(f"Error in experience matching: {e}")
            return 0.0, []
    
    def _calculate_keyword_match(self, job_text: str) -> Tuple[float, Dict[str, int]]:
        """Calculate keyword frequency matches"""
        try:
            # Build keyword list from job search terms
            keywords = {
                "help desk": 0,
                "service desk": 0,
                "infrastructure": 0,
                "architect": 0,
                "cloud": 0,
                "aws": 0,
                "ai": 0,
                "governance": 0,
                "security": 0,
                "network": 0,
                "python": 0,
                "linux": 0,
                "training": 0,
                "leadership": 0,
                "senior": 0,
                "manager": 0,
            }
            
            # Count occurrences
            for keyword in keywords:
                # Use word boundaries for accurate counting
                keywords[keyword] = len(re.findall(r'\b' + re.escape(keyword) + r'\b', job_text))
            
            # Calculate score
            matched = sum(1 for count in keywords.values() if count > 0)
            score = matched / len(keywords) if keywords else 0.0
            
            # Return only matched keywords
            return score, {k: v for k, v in keywords.items() if v > 0}
            
        except Exception as e:
            logger.warning(f"Error in keyword matching: {e}")
            return 0.0, {}
    
    def _check_experience_level(self, job: Dict[str, Any]) -> bool:
        """Check if job experience level matches resume"""
        try:
            title = job.get("title", "").lower()
            exp_level = job.get("experience_level", "").lower()
            
            senior_indicators = [
                "senior", "sr.", "lead", "principal", "architect",
                "manager", "director", "head of"
            ]
            
            # Check if resume indicates senior level
            resume_senior = any(
                indicator in self.resume.get("summary", "").lower()
                for indicator in senior_indicators
            )
            
            job_senior = any(
                indicator in title or indicator in exp_level
                for indicator in senior_indicators
            )
            
            # Match if both are senior or both are not senior
            return resume_senior == job_senior
            
        except Exception as e:
            logger.warning(f"Error checking experience level: {e}")
            return False
    
    def _analyze_fit(
        self, matched: List[str], missing: List[str], relevant_exp: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Analyze strengths and gaps in the match"""
        strengths = []
        gaps = []
        
        try:
            # Strengths
            if len(matched) >= 5:
                strengths.append(f"Strong skill alignment ({len(matched)} matched)")
            
            if len(relevant_exp) >= 2:
                strengths.append(f"Relevant experience ({len(relevant_exp)} positions)")
            
            if any("ai" in s.lower() or "governance" in s.lower() for s in matched):
                strengths.append("AI/Governance expertise aligns with emerging needs")
            
            if any("leadership" in s.lower() or "manager" in s.lower() for s in matched):
                strengths.append("Leadership experience matches requirements")
            
            # Gaps
            critical_missing = [s for s in missing if s.lower() in [
                "aws", "python", "linux", "network security", "cloud"
            ]]
            
            if critical_missing:
                gaps.append(f"Missing critical skills: {', '.join(critical_missing[:3])}")
            elif len(missing) > len(matched):
                gaps.append(f"Skill gap: {len(missing)} skills missing")
            
            if not relevant_exp:
                gaps.append("No directly relevant experience found")
            
        except Exception as e:
            logger.warning(f"Error analyzing fit: {e}")
        
        return strengths, gaps
    
    def _generate_reasoning(
        self,
        score: float,
        skills: float,
        exp: float,
        matched: List[str],
        missing: List[str],
        relevant: List[str],
    ) -> str:
        """Generate concise reasoning summary"""
        parts = [f"Score: {score*100:.1f}%"]
        
        if skills > 0:
            parts.append(f"Skills: {skills*100:.1f}%")
        
        if exp > 0:
            parts.append(f"Experience: {exp*100:.1f}%")
        
        if matched:
            top_skills = ", ".join(matched[:3])
            parts.append(f"Matched: {top_skills}")
        
        if missing and len(missing) <= 3:
            parts.append(f"Missing: {', '.join(missing[:2])}")
        
        return " | ".join(parts)
    
    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on score"""
        if score >= 0.90:
            return "STRONG FIT - Priority application"
        elif score >= 0.85:
            return "VERY GOOD FIT - Highly recommended"
        elif score >= 0.80:
            return "GOOD FIT - Recommended"
        elif score >= 0.70:
            return "MODERATE FIT - Review manually"
        elif score >= 0.60:
            return "LOW FIT - Apply only if interested"
        else:
            return "SKIP - Not a strong match"

def demo_matcher():
    """Demo the matcher with sample jobs"""
    logging.basicConfig(level=logging.INFO)
    
    # Sample jobs
    jobs = [
        {
            "id": "demo_1",
            "title": "Senior IT Infrastructure Architect",
            "company": "TechCorp",
            "description": "We need senior architect with AWS, network security, and leadership skills. Help desk management and AI governance experience preferred.",
        },
        {
            "id": "demo_2",
            "title": "Junior Help Desk Technician",
            "company": "StartUp",
            "description": "Entry level help desk position. Basic computer skills required.",
        },
    ]
    
    matcher = JobMatcher()
    
    print("\n=== MATCHING RESULTS ===\n")
    for job in jobs:
        result = matcher.match_job(job)
        print(f"Job: {job['title']} at {job['company']}")
        print(f"Match Score: {result['match_score']*100:.1f}%")
        print(f"Recommendation: {result['recommendation']}")
        print(f"Reasoning: {result['reasoning']}")
        print()

if __name__ == "__main__":
    demo_matcher()

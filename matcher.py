"""
Job matching engine - Scores jobs against resume with advanced matching algorithms.
"""

import logging
from typing import Dict, List, Tuple, Set, Optional, Any
import difflib
from collections import Counter
import re # Added for better keyword extraction

from config.settings import MATCHING, RESUME_DATA

logger = logging.getLogger(__name__)


class WeightedSkill:
    """Represents a skill with importance weight"""
    def __init__(self, name: str, weight: float = 1.0):
        # Normalize skill name for matching
        self.name = name.lower().strip()
        self.weight = weight


class JobMatcher:
    """
    Match jobs against resume with skill weighting, fuzzy matching, and detailed explanations.
    """
    
    def __init__(self, resume_data: Dict = None):
        # CRITICAL FIX: Load the structured resume data (which includes CORE COMPETENCIES)
        self.resume = resume_data or RESUME_DATA
        
        # 1. Create weighted skills list based on CORE COMPETENCIES
        self.weighted_skills = self._create_weighted_skills()
        
        # 2. Extract keywords from Achievements and Projects
        self.experience_keywords = self._extract_experience_keywords()
        
        # 3. Pre-compile skill variations
        self.skill_variations = self._build_skill_variations()
        
        logger.info(f"✓ JobMatcher initialized with {len(self.weighted_skills)} weighted skills")

    # CRITICAL FIX: Use actual resume structure (CORE COMPETENCIES) and prioritize AI/Governance
    def _create_weighted_skills(self) -> List[WeightedSkill]:
        """ Create weighted skills based on CORE COMPETENCIES and custom certs """
        weighted_skills = []
        
        # Priority mapping for the user's resume sections
        category_weights = {
            "AI & Governance": 3.0,            # Highest priority
            "Operational Leadership": 2.0,     # High priority (Service Desk Automation, SLA)
            "Technical Enablement": 1.2,       # Moderate priority (Python, KPI)
            "Infrastructure Foundation": 1.0,  # Standard priority (Networking, AD)
        }
        
        # Add skills from Core Competencies
        for category, skills in self.resume.get("core_competencies", {}).items():
            weight = category_weights.get(category, 1.0)
            for skill in skills:
                weighted_skills.append(WeightedSkill(skill, weight))

        # Add specific certifications/projects as high-weight skills
        # This addresses the personalization (CompTIA A+ and new AI certs)
        weighted_skills.append(WeightedSkill("ISO/IEC 42001", 2.5))
        weighted_skills.append(WeightedSkill("Generative AI Strategy", 2.2))
        weighted_skills.append(WeightedSkill("CompTIA A+", 1.1)) # Lower weight, but relevant for support roles
        weighted_skills.append(WeightedSkill("AI-Powered Triage", 2.2))

        # Deduplicate skills, keeping the highest weight if duplicated
        unique_skills = {}
        for skill in weighted_skills:
            if skill.name not in unique_skills or skill.weight > unique_skills[skill.name].weight:
                unique_skills[skill.name] = skill
        
        return list(unique_skills.values())

    # CRITICAL FIX: Simplify and standardize variations
    def _build_skill_variations(self) -> Dict[str, Set[str]]:
        """ Build variations of skills for fuzzy matching (exact matching only for speed) """
        variations = {}
        for skill in self.weighted_skills:
            name = skill.name
            var_set = {name}
            
            # Common abbreviations and multi-word variations
            if "aws" in name: var_set.add("amazon web services")
            if "ad" in name: var_set.add("active directory")
            if "vpn" in name: var_set.add("virtual private network")
            if "ci/cd" in name: var_set.add("cicd")
            if "service desk" in name: var_set.add("help desk")
            if "iso/iec 42001" in name: var_set.add("iso 42001")
            
            variations[name] = var_set
        
        return variations

    # CRITICAL FIX: Extract keywords from ACHIEVEMENTS and PROJECTS
    def _extract_experience_keywords(self) -> Set[str]:
        """Extract keywords from experience achievements and projects"""
        keywords = set()
        
        # Keywords from Professional Experience achievements
        for exp in self.resume.get("experience", []):
            for achievement in exp.get("achievements", []):
                # Extract words related to IT operations, results, and management
                words = re.findall(r'\b(?:[A-Z]{2,}(?:\/[A-Z]{2,})?|modernizing|automating|architected|compliance|governance|reducing|led|delivered|managed|optimized|security|network)\b', achievement, re.IGNORECASE)
                keywords.update(word.lower() for word in words)

        # Keywords from Technical Projects (high relevance)
        for proj in self.resume.get("projects", []):
            keywords.add(proj["name"].lower())
            for achievement in proj.get("achievements", []):
                words = re.findall(r'\b(?:python|triage|classification|safeguards|audit|compliance|validation)\b', achievement, re.IGNORECASE)
                keywords.update(word.lower() for word in words)

        return keywords

    def match_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive match score with explanations.
        """
        job_text = f"{job['title']} {job.get('description', '')} {job.get('requirements', '')}".lower()

        # 1. Skills matching (40%)
        skills_score, matched_skills, missing_skills, skill_details = self._calculate_weighted_skills_match(job_text)

        # 2. Experience relevance (40%)
        experience_score, relevant_exp, exp_details = self._calculate_experience_match(job_text)

        # 3. Keyword match (20%)
        keyword_score, keyword_matches = self._calculate_keyword_match(job_text)

        # Calculate weighted score
        base_score = (
            MATCHING["weights"]["skills"] * skills_score +
            MATCHING["weights"]["experience"] * experience_score +
            MATCHING["weights"]["keywords"] * keyword_score
        )

        # Experience level adjustment
        exp_level_result = self._check_experience_level(job)
        multiplier = exp_level_result["multiplier"]

        match_score = base_score * multiplier

        # Generate detailed analysis
        strengths, gaps = self._analyze_fit(matched_skills, missing_skills, relevant_exp)
        
        # Generate human-readable explanation
        explanation = self._generate_detailed_explanation(
            match_score, skills_score, experience_score, keyword_score, multiplier, exp_level_result
        )

        # Recommendation
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
            "reasoning": explanation,
            "scores": {
                "skills": skills_score,
                "experience": experience_score,
                "keywords": keyword_score,
            },
            "match_details": { 
                "skill_details": skill_details,
                "experience_details": exp_details,
                "level_adjustment": multiplier,
            }
        }

    def _calculate_weighted_skills_match(self, job_text: str) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
        """Calculate weighted skills match using exact and variation matching"""
        matched_skills = []
        matched_weight = 0.0
        total_weight = sum(skill.weight for skill in self.weighted_skills)
        job_words = set(job_text.split()) # Optimized: create word set once
        
        skill_details = []
        
        for skill in self.weighted_skills:
            found = False
            
            # Check for exact matches and common variations (faster and more accurate than fuzzy)
            variations = self.skill_variations.get(skill.name, {skill.name})
            
            for var in variations:
                if var in job_text:
                    matched_skills.append(skill.name.title())
                    matched_weight += skill.weight
                    skill_details.append({
                        "skill": skill.name,
                        "type": "exact/variation",
                        "weight": skill.weight
                    })
                    found = True
                    break # Move to next resume skill
            
            if found:
                continue
            
            # Use fuzzy matching as a very limited fallback (original logic for reference)
            best_match = self._find_fuzzy_match(skill.name, job_words)
            if best_match and best_match[1] > 0.75:
                matched_skills.append(skill.name.title())
                matched_weight += skill.weight * 0.9
                skill_details.append({
                    "skill": skill.name,
                    "type": "fuzzy",
                    "matched_text": best_match[0],
                    "similarity": best_match[1],
                    "weight": skill.weight * 0.9
                })

        score = matched_weight / total_weight if total_weight > 0 else 0.0
        # Missing skills list includes titles for display
        missing_skills = [skill.name.title() for skill in self.weighted_skills 
                         if skill.name.title() not in matched_skills]
        
        return score, matched_skills, missing_skills, {"details": skill_details}

    # Simplified fuzzy match to run against a smaller context set if possible
    def _find_fuzzy_match(self, skill: str, words: set) -> Optional[Tuple[str, float]]:
        """Find fuzzy match for a skill within a pre-computed set of words."""
        
        # Use difflib for partial matches only against the isolated words
        matches = difflib.get_close_matches(skill, words, n=1, cutoff=0.75)
        
        if matches:
            return (matches[0], difflib.SequenceMatcher(None, skill, matches[0]).ratio())
        
        return None

    def _calculate_experience_match(self, job_text: str) -> Tuple[float, List[str], Dict[str, Any]]:
        """Calculate experience relevance based on a more sophisticated scoring model."""
        relevant_exp = []
        exp_details = []
        total_score = 0.0
        max_possible_score = 0.0

        for exp in self.resume.get("experience", []):
            position_score = 0.0
            details = {"position": f"{exp['title']} at {exp['company']}", "score_breakdown": {}}

            # 1. Title Keyword Overlap Score (Max: 30 points)
            resume_title_keywords = set(exp["title"].lower().split())
            job_text_keywords = set(job_text.split())
            common_keywords = resume_title_keywords.intersection(job_text_keywords)
            if common_keywords:
                position_score += 15
                if len(common_keywords) > 1:
                    position_score += 15 # Extra points for more overlap
                details["score_breakdown"]["title_match"] = 15 + (15 if len(common_keywords) > 1 else 0)

            # 2. Achievement Analysis (Max: 70 points)
            achievement_score = 0
            has_quantification = False
            has_ai_governance = False

            for achievement in exp.get("achievements", []):
                # Check for quantification
                if re.search(r'\d+', achievement):
                    has_quantification = True
                # Check for AI/Governance keywords
                if "ai" in achievement.lower() or "governance" in achievement.lower():
                    has_ai_governance = True

            # Score based on findings
            if has_quantification and ("metric" in job_text or "kpi" in job_text):
                achievement_score += 30
                details["score_breakdown"]["quantification"] = 30
            if has_ai_governance and ("ai" in job_text or "governance" in job_text):
                achievement_score += 40
                details["score_breakdown"]["ai_governance"] = 40
            
            position_score += achievement_score
            
            if position_score > 30: # Only include positions with a meaningful score
                relevant_exp.append(f"{exp['title']} at {exp['company']}")
                exp_details.append(details)

            total_score += position_score
            max_possible_score += 100 # Each position is worth 100 points

        final_score = total_score / max_possible_score if max_possible_score > 0 else 0.0
        return final_score, relevant_exp, {"positions": exp_details}

    def _calculate_keyword_match(self, job_text: str) -> Tuple[float, Dict[str, int]]:
        """Calculate keyword matches with frequency weighting, prioritizing AI/Governance"""
        keywords = {
            "ai governance": 0,
            "iso 42001": 0,
            "service desk": 0,
            "triage": 0,
            "python": 0,
            "architect": 0,
            "leadership": 0,
            "security": 0,
            "comptia a+": 0,
            "manager": 0,
        }
        
        # Count occurrences with bonus for multiple mentions
        for keyword in keywords:
            count = job_text.count(keyword)
            if count > 0:
                # Assign a weighted count: 1 for first, 0.5 for subsequent
                keywords[keyword] = count + (0.5 * max(0, count - 1))
        
        total_weight = sum(keywords.values())
        max_possible = len(keywords) * 2  
        score = min(total_weight / max_possible, 1.0)
        
        return score, {k: int(v) for k, v in keywords.items() if v > 0}

    def _check_experience_level(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced experience level matching: checks if job aligns with the user's Senior/Architect level.
        """
        title = job["title"].lower()
        description = job.get("description", "").lower()
        combined_text = f"{title} {description}"
        
        # User is positioned as 'Senior/Lead/Architect'
        user_level_indicators = ["senior", "sr.", "lead", "principal", "staff", "architect", "manager", "director"]
        
        # Check if the job explicitly contains high-level indicators
        is_job_senior_level = any(indicator in combined_text for indicator in user_level_indicators)
        
        # Check for junior/entry level terms (which would negatively impact the multiplier)
        is_job_junior_level = any(indicator in combined_text for indicator in ["junior", "jr.", "entry", "associate", "level 1"])
        
        multiplier = 1.0
        
        if is_job_junior_level and not is_job_senior_level:
            # Low multiplier if it's explicitly junior/entry
            multiplier = MATCHING["experience_level_multiplier"] * 0.5
        elif not is_job_senior_level and not is_job_junior_level:
            # Standard penalty if no high-level terms detected (might be a mid-level role)
            multiplier = MATCHING["experience_level_multiplier"]
        
        return {
            "matches": is_job_senior_level,
            "is_senior": is_job_senior_level,
            "multiplier": multiplier
        }

    def _analyze_fit(self, matched: List[str], missing: List[str], relevant_exp: List[str]) -> Tuple[List[str], List[str]]:
        """Analyze strengths and gaps with nuance"""
        strengths = []
        gaps = []
        
        # Skill strength analysis (Weighted match for AI/Governance)
        ai_gov_skills = ["iso/iec 42001", "generative ai strategy", "ai-powered triage"]
        matched_ai_gov = [s for s in matched if s.lower() in ai_gov_skills]
        
        if matched_ai_gov:
            strengths.append(f"CORE STRENGTH: Expertise in {', '.join(matched_ai_gov)}.")
        
        if len(relevant_exp) >= 2:
            strengths.append(f"Deep operational background ({len(relevant_exp)} relevant positions).")
        
        # Gap analysis
        if len(missing) >= 4:
            gaps.append(f"Significant gaps: Missing {len(missing)} key skills, including {', '.join(missing[:3])}.")
        elif missing:
            gaps.append(f"Minor gaps: Could strengthen knowledge in {', '.join(missing[:2])}.")
        
        return strengths, gaps

    def _generate_detailed_explanation(self, score: float, skills_score: float, experience_score: float, 
                                      keyword_score: float, multiplier: float, level_result: Dict) -> str:
        """
        Generate detailed human-readable explanation of the score components.
        """
        parts = []
        
        # Weighted Score Breakdown
        parts.append(f"Skills Fit: {skills_score*100:.1f}% ({MATCHING['weights']['skills']:.0%} weight)")
        parts.append(f"Experience Fit: {experience_score*100:.1f}% ({MATCHING['weights']['experience']:.0%} weight)")
        parts.append(f"Keyword/Topic Fit: {keyword_score*100:.1f}% ({MATCHING['weights']['keywords']:.0%} weight)")
        
        # Level adjustment summary
        if multiplier < 1.0:
            penalty = 1.0 - multiplier
            parts.append(f"Level Adjustment: Penalty applied (-{penalty*100:.0f}%) due to perceived non-senior role fit.")
        elif level_result["is_senior"]:
            parts.append("Level Adjustment: Senior role fit confirmed (100% multiplier).")
        
        return " | ".join(parts)

    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on score thresholds"""
        if score >= 0.85:
            return "EXCELLENT FIT - Strongly recommended for tailoring"
        elif score >= 0.75:
            return "STRONG FIT - Highly recommended for tailoring"
        elif score >= 0.65:
            return "GOOD FIT - Recommended for tailoring review"
        elif score >= 0.55:
            return "MODERATE FIT - Requires manual review"
        else:
            return "SKIP - Not a strong match"

    def generate_match_report(self, job: Dict[str, Any]) -> str:
        """
        Generate comprehensive match report
        """
        result = self.match_job(job)
        
        report = []
        report.append("=" * 80)
        report.append(f"🎯 Match Report: {job['title']} at {job['company']}")
        report.append("=" * 80)
        report.append(f"Overall Score: **{result['match_score']*100:.1f}%**")
        report.append(f"Recommendation: **{result['recommendation']}**")
        report.append("---")
        
        report.append("## 📊 Score Breakdown")
        report.append(result["reasoning"])
        report.append("---")

        if result["strengths"]:
            report.append("## 💪 Strengths")
            for strength in result["strengths"]:
                report.append(f"  ✓ {strength}")
            report.append("---")
        
        if result["gaps"]:
            report.append("## 🚧 Gaps")
            for gap in result["gaps"]:
                report.append(f"  ✗ {gap}")
            report.append("---")
        
        report.append("## 🔍 Details")
        report.append(f"**Matched Skills ({len(result['matched_skills'])}):** {', '.join(result['matched_skills'])}")
        report.append(f"**Relevant Experience ({len(result['relevant_experience'])}):**")
        for exp in result["relevant_experience"]:
            report.append(f"  - {exp}")
        
        return "\n".join(report)


def demo_matcher() -> None:
    """ Demo the matcher with detailed output """
    
    # Mock MATCHING data for demo purposes
    mock_matching = {
        "weights": {"skills": 0.40, "experience": 0.40, "keywords": 0.20},
        "experience_level_multiplier": 0.80
    }
    
    # Mock resume data based on the structure extracted from your updated resume
    mock_resume_data = {
        "core_competencies": {
            "AI & Governance": ["ISO/IEC 42001 Standards", "Generative AI Strategy", "Risk Management"],
            "Operational Leadership": ["Service Desk Automation", "SLA Optimization", "Vendor Management"],
            "Technical Enablement": ["Python (Automation)", "KPI Reporting"],
            "Infrastructure Foundation": ["Network Security Protocols", "Identity & Access Management (AD/LDAP)"]
        },
        "experience": [
            {"company": "CIMSYSTEM", "title": "Technical Operations Lead & Specialist", "dates": "2018 - 2025", "achievements": ["Achieved 99% uptime and aggressive SLA compliance", "Built centralized SOP library, reducing onboarding time by 50%"]},
            {"company": "ACCUCODE", "title": "Network Infrastructure Architect", "dates": "2017 - 2018", "achievements": ["Engineered secure network architecture", "Managed VPN/firewall configurations"]},
        ],
        "projects": [
            {"name": "AI-Powered Triage & Classification Engine", "achievements": ["Automated Tier 1 ticket classification", "Aligned with ISO/IEC 42001 transparency principles"]},
        ],
    }

    # Demo jobs (using the structure defined in scraper.py)
    job1 = {
        "id": "A123",
        "title": "Senior AI Governance Strategy Lead",
        "company": "Global Systems",
        "description": "Seeking a leader to establish ISO/IEC 42001 compliant AI Governance frameworks. Must have deep experience in Python automation for Service Desk Triage and risk management.",
        "experience_level": "Senior",
        "requirements": "10+ years experience, expert in Network Security and KPI reporting. Senior level role.",
    }
    
    job2 = {
        "id": "B456",
        "title": "Entry Level Help Desk Analyst",
        "company": "Local Support",
        "description": "Join our junior team. Must have CompTIA A+ and basic knowledge of Active Directory. Focus on Tier 1 support and basic network troubleshooting.",
        "experience_level": "Junior",
        "requirements": "CompTIA A+ required. No senior experience needed.",
    }
    
    # Temporarily set globals for demo
    global MATCHING, RESUME_DATA
    original_matching = MATCHING
    original_resume_data = RESUME_DATA
    
    MATCHING = mock_matching
    RESUME_DATA = mock_resume_data

    matcher = JobMatcher()
    
    print("\n=== MATCHING RESULTS ===\n")
    for job in [job1, job2]:
        print(matcher.generate_match_report(job))
        print("\n")
        
    # Restore globals
    MATCHING = original_matching
    RESUME_DATA = original_resume_data


if __name__ == "__main__":
    demo_matcher()

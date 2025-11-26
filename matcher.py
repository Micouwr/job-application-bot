"""
Job matching engine - Scores jobs against resume with advanced matching algorithms.
"""

import logging
from typing import Dict, List, Tuple, Set
import difflib  # For fuzzy matching
from collections import Counter

from config.settings import MATCHING, RESUME_DATA

logger = logging.getLogger(__name__)


class WeightedSkill:
    """Represents a skill with importance weight"""
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name.lower()
        self.weight = weight


class JobMatcher:
    """
    Match jobs against resume with skill weighting, fuzzy matching, and detailed explanations.
    """
    
    def __init__(self, resume_data: Dict = None):
        self.resume = resume_data or RESUME_DATA
        
        # Create weighted skills list
        self.weighted_skills = self._create_weighted_skills()
        self.experience_keywords = self._extract_experience_keywords()
        
        # Pre-compile skill variations for fuzzy matching
        self.skill_variations = self._build_skill_variations()
        
        logger.info(f"✓ JobMatcher initialized with {len(self.weighted_skills)} weighted skills")

    def _create_weighted_skills(self) -> List[WeightedSkill]:
        """Create weighted skills based on categories"""
        weighted_skills = []
        
        # Higher weight for advanced skills
        category_weights = {
            "ai_cloud": 1.5,
            "infrastructure_security": 1.3,
            "service_leadership": 1.2,
            "technical": 1.0
        }
        
        for category, skills in self.resume["skills"].items():
            weight = category_weights.get(category, 1.0)
            for skill in skills:
                weighted_skills.append(WeightedSkill(skill, weight))
        
        return weighted_skills

    def _build_skill_variations(self) -> Dict[str, Set[str]]:
        """Build variations of skills for fuzzy matching"""
        variations = {}
        for skill in self.weighted_skills:
            # Create variations (AWS -> Amazon Web Services, etc.)
            var_set = {skill.name}
            
            # Add common abbreviations
            if skill.name == "aws":
                var_set.add("amazon web services")
            elif skill.name == "active directory":
                var_set.add("ad")
            elif skill.name == "vpn":
                var_set.add("virtual private network")
            
            variations[skill.name] = var_set
        
        return variations

    def _extract_experience_keywords(self) -> Set[str]:
        """  Extract keywords from experience with weights """
        keywords = set()
        for exp in self.resume["experience"]:
            for skill in exp.get("skills_used", []):
                keywords.add(skill.lower())
            # Add key terms from achievements
            for achievement in exp.get("achievements", []):
                # Extract important words (verbs, nouns)
                words = [word.lower() for word in achievement.split() 
                        if len(word) > 3 and word not in {"the", "and", "for", "with"}]
                keywords.update(words)
        return keywords

    def match_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive match score with explanations.
        
        Returns:
            Dictionary with score, matched skills, analysis, and human-readable explanation
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

        # Experience level adjustment with detailed logic
        exp_level_result = self._check_experience_level(job)
        multiplier = 1.0 if exp_level_result["matches"] else MATCHING["experience_level_multiplier"]

        match_score = base_score * multiplier

        # Generate detailed analysis
        strengths, gaps = self._analyze_fit(matched_skills, missing_skills, relevant_exp)
        
        # Generate human-readable explanation
        explanation = self._generate_detailed_explanation(
            match_score, skill_details, exp_details, multiplier, exp_level_result
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
            "match_details": {  # ✅ QoL: Detailed breakdown
                "skill_details": skill_details,
                "experience_details": exp_details,
                "level_adjustment": multiplier,
            }
        }

    def _calculate_weighted_skills_match(self, job_text: str) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
        """Calculate weighted skills match with fuzzy matching"""
        matched_skills = []
        matched_weight = 0.0
        total_weight = sum(skill.weight for skill in self.weighted_skills)
        
        skill_details = []
        
        for skill in self.weighted_skills:
            # Check for exact match
            if skill.name in job_text:
                matched_skills.append(skill.name.title())
                matched_weight += skill.weight
                skill_details.append({
                    "skill": skill.name,
                    "type": "exact",
                    "weight": skill.weight
                })
                continue
            
            # Check for fuzzy match
            best_match = self._find_fuzzy_match(skill.name, job_text)
            if best_match and best_match[1] > 0.8:  # 80% similarity threshold
                matched_skills.append(skill.name.title())
                matched_weight += skill.weight * 0.9  # Slightly reduce weight for fuzzy matches
                skill_details.append({
                    "skill": skill.name,
                    "type": "fuzzy",
                    "matched_text": best_match[0],
                    "similarity": best_match[1],
                    "weight": skill.weight * 0.9
                })

        if not self.weighted_skills:
            return 0.0, [], [], {}
        
        # ✅ Fixed: Explicit check for empty skills
        score = matched_weight / total_weight if total_weight > 0 else 0.0
        missing_skills = [skill.name.title() for skill in self.weighted_skills 
                         if skill.name.title() not in matched_skills]
        
        return score, matched_skills, missing_skills, {"details": skill_details}

    def _find_fuzzy_match(self, skill: str, text: str) -> Optional[Tuple[str, float]]:
        """Find fuzzy match for skill in text"""
        # Check direct variations first
        if skill in self.skill_variations:
            for variation in self.skill_variations[skill]:
                if variation in text:
                    return (variation, 1.0)
        
        # Use difflib for partial matches
        words = text.split()
        matches = difflib.get_close_matches(skill, words, n=1, cutoff=0.8)
        
        if matches:
            return (matches[0], difflib.SequenceMatcher(None, skill, matches[0]).ratio())
        
        return None

    def _calculate_experience_match(self, job_text: str) -> Tuple[float, List[str], Dict[str, Any]]:
        """  Calculate experience relevance with details """
        relevant_exp = []
        exp_details = []
        score = 0.0
        
        for exp in self.resume["experience"]:
            relevance = 0.0
            details = {"position": f"{exp['title']} at {exp['company']}"}
            
            # Title matching
            if exp["title"].lower() in job_text:
                relevance += 0.5
                details["title_match"] = True
            
            # Skills matching with bonus for multiple matches
            skill_matches = []
            for skill in exp.get("skills_used", []):
                if skill.lower() in job_text:
                    relevance += 0.1
                    skill_matches.append(skill)
            
            details["skill_matches"] = skill_matches
            
            if relevance > 0.2:
                relevant_exp.append(f"{exp['title']} at {exp['company']} ({exp['dates']})")
                exp_details.append(details)
                score += min(relevance, 0.8)  # Cap at 0.8 per position
        
        # ✅  Fixed: Explicit capping
        final_score = min(score, 1.0)
        return final_score, relevant_exp, {"positions": exp_details}

    def _calculate_keyword_match(self, job_text: str) -> Tuple[float, Dict[str, int]]:
        """  Calculate keyword matches with frequency weighting """
        keywords = {
            "help desk": 0,
            "service desk": 0,
            "infrastructure": 0,
            "architect": 0,
            "cloud": 0,
            "ai": 0,
            "governance": 0,
            "training": 0,
            "leadership": 0,
            "senior": 0,
            "manager": 0,
        }
        
        # Count occurrences with bonus for multiple mentions
        for keyword in keywords:
            count = job_text.count(keyword)
            if count > 0:
                # Bonus points for repeated mentions
                keywords[keyword] = count + (0.5 * max(0, count - 1))
        
        matched = sum(1 for count in keywords.values() if count > 0)
        # Calculate score with bonus for frequency
        total_weight = sum(keywords.values())
        max_possible = len(keywords) * 2  # Assume max 2 mentions per keyword
        score = min(total_weight / max_possible, 1.0)
        
        return score, {k: int(v) for k, v in keywords.items() if v > 0}

    def _check_experience_level(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Fixed: Enhanced experience level matching
        Returns detailed analysis instead of just boolean
        """
        title = job["title"].lower()
        exp_level = job.get("experience_level", "").lower()
        description = job.get("description", "").lower()
        
        # Combine all text for comprehensive check
        combined_text = f"{title} {exp_level} {description}"
        
        level_indicators = {
            "senior": ["senior", "sr.", "sr", "lead", "principal", "staff", "architect", "manager", "director"],
            "mid": ["mid", "intermediate", "ii", "2"],
            "junior": ["junior", "jr.", "jr", "entry", "associate", "i", "1"]
        }
        
        detected_levels = []
        for level, indicators in level_indicators.items():
            if any(indicator in combined_text for indicator in indicators):
                detected_levels.append(level)
        
        # Check if job is senior-level (what resume indicates)
        is_senior = "senior" in detected_levels
        matches = bool(detected_levels)  # True if we could detect a level
        
        return {
            "matches": matches,
            "detected_levels": detected_levels,
            "is_senior": is_senior,
            "multiplier": 1.0 if is_senior else MATCHING["experience_level_multiplier"]
        }

    def _analyze_fit(self, matched: List[str], missing: List[str], relevant_exp: List[str]) -> Tuple[List[str], List[str]]:
        """Analyze strengths and gaps with more nuance"""
        strengths = []
        gaps = []
        
        # Skill strength analysis
        if len(matched) >= 5:
            strengths.append(f"Strong skill alignment ({len(matched)} matched skills)")
        elif len(matched) >= 3:
            strengths.append(f"Moderate skill alignment ({len(matched)} matched skills)")
        
        # Experience strength
        if len(relevant_exp) >= 3:
            strengths.append(f"Extensive relevant experience ({len(relevant_exp)} positions)")
        elif len(relevant_exp) >= 2:
            strengths.append(f"Relevant experience ({len(relevant_exp)} positions)")
        
        # AI/Governance specialization bonus
        ai_gov_skills = ["ai governance", "iso/iec 42001", "generative ai"]
        if any(skill.lower() in [m.lower() for m in matched] for skill in ai_gov_skills):
            strengths.append("AI/Governance expertise aligns with emerging needs")
        
        # Gap analysis
        if missing and len(missing) > len(matched):
            gaps.append(f"Missing {len(missing)} key skills: {', '.join(missing[:3])}")
        elif missing:
            gaps.append(f"Could strengthen: {', '.join(missing[:2])}")
        
        return strengths, gaps

    def _generate_detailed_explanation(self, score: float, skill_details: Dict, exp_details: Dict, 
                                      multiplier: float, level_result: Dict) -> str:
        """
        ✅ QoL: Generate detailed human-readable explanation
        """
        parts = [f"Overall: {score*100:.1f}%"]
        
        # Skill breakdown
        if skill_details.get("details"):
            skill_score = sum(d.get("weight", 0) for d in skill_details["details"])
            parts.append(f"Skills: {skill_score:.2f} weighted matches")
        
        # Experience breakdown
        if exp_details.get("positions"):
            exp_count = len(exp_details["positions"])
            parts.append(f"Experience: {exp_count} relevant positions")
        
        # Level adjustment
        if not level_result["matches"]:
            parts.append(f"Experience level unclear (-{100 - multiplier*100:.0f}%)")
        elif not level_result["is_senior"]:
            parts.append(f"May be junior to role (-{100 - multiplier*100:.0f}%)")
        
        return " | ".join(parts)

    def _get_recommendation(self, score: float) -> str:
        """  Get recommendation based on score thresholds """
        if score >= 0.90:
            return "EXCELLENT FIT - Strongly recommended"
        elif score >= 0.85:
            return "STRONG FIT - Highly recommended"
        elif score >= 0.80:
            return "GOOD FIT - Recommended"
        elif score >= 0.70:
            return "MODERATE FIT - Review manually"
        elif score >= 0.60:
            return "POOR FIT - Consider only if gaps can be addressed"
        else:
            return "SKIP - Not a strong match"

    def generate_match_report(self, job: Dict[str, Any]) -> str:
        """
        ✅ QoL: Generate comprehensive match report
        """
        result = self.match_job(job)
        
        report = []
        report.append("=" * 80)
        report.append(f"Match Report: {job['title']} at {job['company']}")
        report.append("=" * 80)
        report.append(f"Overall Score: {result['match_score']*100:.1f}%")
        report.append(f"Recommendation: {result['recommendation']}")
        report.append("")
        
        if result["strengths"]:
            report.append("STRENGTHS:")
            for strength in result["strengths"]:
                report.append(f"  ✓ {strength}")
            report.append("")
        
        if result["gaps"]:
            report.append("GAPS:")
            for gap in result["gaps"]:
                report.append(f"  ✗ {gap}")
            report.append("")
        
        if result["match_details"]:
            report.append("DETAILED BREAKDOWN:")
            for key, value in result["match_details"].items():
                report.append(f"  {key}: {value}")
        
        return "\n".join(report)


def demo_matcher() -> None:
    """  Demo the matcher with detailed output """
    from scraper import demo_scraper
    
    jobs = demo_scraper()
    matcher = JobMatcher()
    
    print("\n=== MATCHING RESULTS ===\n")
    for job in jobs:
        result = matcher.match_job(job)
        print(matcher.generate_match_report(job))
        print("\n")


if __name__ == "__main__":
    demo_matcher()

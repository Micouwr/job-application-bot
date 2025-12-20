"""
Job Description Parser Utilities
Support for parsing job descriptions from various sources:
- LinkedIn job postings
- Email applications
- Plain text job descriptions
"""

import re
from typing import Dict, Optional
import json


def parse_linkedin_job_description(html_content: str) -> Dict[str, str]:
    """
    Parse job description from LinkedIn job posting HTML content.
    
    Args:
        html_content (str): HTML content of LinkedIn job posting
        
    Returns:
        Dict with parsed job details:
        - title: Job title
        - company: Company name
        - location: Job location
        - description: Full job description text
    """
    # This is a simplified parser - in reality, you'd want to use BeautifulSoup
    # or similar HTML parsing library for robust parsing
    
    job_data = {
        'title': 'Unknown Position',
        'company': 'Unknown Company',
        'location': 'Unknown Location',
        'description': ''
    }
    
    # Extract job title (simplified regex approach)
    title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html_content, re.IGNORECASE)
    if title_match:
        job_data['title'] = title_match.group(1).strip()
    
    # Extract company name
    company_match = re.search(r'<span[^>]*class="topcard__flavor"[^>]*>([^<]+)</span>', html_content, re.IGNORECASE)
    if company_match:
        job_data['company'] = company_match.group(1).strip()
    
    # Extract location
    location_match = re.search(r'<span[^>]*class="topcard__flavor[^"]*topcard__flavor--bullet"[^>]*>([^<]+)</span>', html_content, re.IGNORECASE)
    if location_match:
        job_data['location'] = location_match.group(1).strip()
    
    # Extract job description (look for the main description div)
    desc_start = html_content.find('description__text')
    if desc_start != -1:
        # Find the closing div tag after the start
        desc_end = html_content.find('</div>', desc_start)
        if desc_end != -1:
            # Extract content between tags
            desc_section = html_content[desc_start:desc_end]
            # Remove HTML tags
            clean_desc = re.sub(r'<[^>]+>', '', desc_section)
            job_data['description'] = clean_desc.strip()
    
    # If we couldn't extract description properly, try alternative approach
    if not job_data['description']:
        # Look for any large block of text that might be the description
        desc_matches = re.findall(r'<div[^>]*class="show-more-less-html__markup"[^>]*>(.*?)</div>', html_content, re.DOTALL | re.IGNORECASE)
        if desc_matches:
            # Take the longest match as it's likely the full description
            longest_desc = max(desc_matches, key=len)
            clean_desc = re.sub(r'<[^>]+>', '', longest_desc)
            job_data['description'] = clean_desc.strip()
    
    return job_data


def parse_email_job_description(email_content: str) -> Dict[str, str]:
    """
    Parse job description from email content.
    
    Args:
        email_content (str): Raw email content
        
    Returns:
        Dict with parsed job details
    """
    job_data = {
        'title': 'Unknown Position',
        'company': 'Unknown Company',
        'location': 'Unknown Location',
        'description': email_content.strip()
    }
    
    # Try to extract job title from subject line patterns
    title_patterns = [
        r'(?:job|position)[:\s]+(.+?)(?:\sat\s|$)',
        r'(?:opening|opportunity)[:\s]+(.+?)(?:\sat\s|$)',
        r'(?:hiring\s+for\s+)(.+?)(?:\s+position|$)'
    ]
    
    for pattern in title_patterns:
        title_match = re.search(pattern, email_content, re.IGNORECASE)
        if title_match:
            job_data['title'] = title_match.group(1).strip()
            break
    
    # Try to extract company name
    company_patterns = [
        r'(?:at|@)\s+([A-Z][a-zA-Z\s&\-]+?)(?:\.|\n|$)',
        r'(?:company|employer)[:\s]+([A-Z][a-zA-Z\s&\-]+?)(?:\.|\n|$)'
    ]
    
    for pattern in company_patterns:
        company_match = re.search(pattern, email_content, re.IGNORECASE)
        if company_match:
            job_data['company'] = company_match.group(1).strip()
            break
    
    return job_data


def parse_plain_text_job_description(text_content: str) -> Dict[str, str]:
    """
    Parse job description from plain text content.
    
    Args:
        text_content (str): Plain text job description
        
    Returns:
        Dict with parsed job details
    """
    # For plain text, we'll use basic heuristics to identify sections
    lines = text_content.strip().split('\n')
    
    job_data = {
        'title': 'Unknown Position',
        'company': 'Unknown Company',
        'location': 'Unknown Location',
        'description': text_content.strip()
    }
    
    # If we have multiple lines, try to parse them
    if len(lines) > 1:
        # First line might be title
        first_line = lines[0].strip()
        if first_line and len(first_line) < 100 and not first_line.startswith(('http', 'www')):
            job_data['title'] = first_line
            
        # Second line might contain company
        if len(lines) > 1:
            second_line = lines[1].strip()
            if ' at ' in second_line or ' @ ' in second_line:
                # Extract company from "Position at Company" format
                parts = re.split(r'\s+(?:at|@)\s+', second_line, re.IGNORECASE)
                if len(parts) > 1:
                    job_data['company'] = parts[-1]
    
    return job_data


def extract_job_requirements(description: str) -> Dict[str, list]:
    """
    Extract common job requirements from job description.
    
    Args:
        description (str): Job description text
        
    Returns:
        Dict with extracted requirements:
        - skills: Technical skills
        - experience: Experience requirements
        - education: Education requirements
        - benefits: Benefits mentioned
    """
    requirements = {
        'skills': [],
        'experience': [],
        'education': [],
        'benefits': []
    }
    
    # Convert to lowercase for easier matching
    desc_lower = description.lower()
    
    # Common skill keywords
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'docker', 'kubernetes',
        'aws', 'azure', 'gcp', 'machine learning', 'ai', 'tensorflow', 'pytorch',
        'html', 'css', 'angular', 'vue.js', 'spring', 'django', 'flask', 'rails',
        'c++', 'c#', 'go', 'rust', 'scala', 'kotlin', 'swift', 'objective-c'
    ]
    
    # Extract skills
    for skill in skill_keywords:
        if skill in desc_lower:
            requirements['skills'].append(skill.title())
    
    # Extract experience requirements (X+ years patterns)
    exp_patterns = [
        r'(\d+)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)',
        r'(?:experience|exp)\s+(?:of\s+)?(\d+)\s*\+?\s*(?:years?|yrs?)'
    ]
    
    for pattern in exp_patterns:
        exp_matches = re.findall(pattern, desc_lower)
        for match in exp_matches:
            requirements['experience'].append(f"{match}+ years experience")
    
    # Extract education requirements
    edu_patterns = [
        r"(?:bachelor|master|ph\.?d|m\.?s|b\.?s)'?s?.*?(?:degree|in)",
        r"(?:degree|diploma).*?(?:computer science|engineering|mathematics|statistics)",
        r"(?:computer science|engineering|mathematics|statistics).*?(?:degree|diploma)"
    ]
    
    for pattern in edu_patterns:
        edu_match = re.search(pattern, desc_lower)
        if edu_match:
            requirements['education'].append(edu_match.group(0))
    
    # Extract benefits (simplified)
    benefit_keywords = [
        'health insurance', 'dental insurance', 'vision insurance', '401k', 'retirement plan',
        'pto', 'paid time off', 'vacation', 'remote work', 'work from home',
        'flexible hours', 'unlimited pto', 'stock options', 'bonus', 'competitive salary'
    ]
    
    for benefit in benefit_keywords:
        if benefit in desc_lower:
            requirements['benefits'].append(benefit.title())
    
    return requirements


# Example usage and testing
if __name__ == "__main__":
    # Test with sample data
    sample_linkedin = '''
    <h1>Senior Software Engineer</h1>
    <span class="topcard__flavor">TechCorp Inc.</span>
    <span class="topcard__flavor topcard__flavor--bullet">Louisville, KY</span>
    <div class="description__text">
        <div class="show-more-less-html__markup">
            <p>We are looking for a Senior Software Engineer to join our team.</p>
            <p>Requirements:</p>
            <ul>
                <li>5+ years of Python experience</li>
                <li>Experience with Django and REST APIs</li>
                <li>Bachelor's degree in Computer Science</li>
            </ul>
        </div>
    </div>
    '''
    
    parsed = parse_linkedin_job_description(sample_linkedin)
    print("Parsed LinkedIn job:")
    print(json.dumps(parsed, indent=2))
    
    requirements = extract_job_requirements(parsed['description'])
    print("\nExtracted requirements:")
    print(json.dumps(requirements, indent=2))
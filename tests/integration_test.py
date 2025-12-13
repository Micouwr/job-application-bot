#!/usr/bin/env python3
"""
Integration test: Verify AI modules work when imported by GUI
SAVE POINT #153 - Pre-GUI Integration Test
"""

import sys
from pathlib import Path

# CRITICAL FIX: Point to project root (parent of tests/)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from AI.match_analyzer import analyze_match
from AI.tailor_engine import tailor_resume, generate_cover_letter

def test_ai_integration():
    """Test AI modules can be imported and called from GUI context"""
    print("=== SAVE POINT #153 Integration Test ===")
    
    # Test data
    resume = """Senior Software Engineer with 5 years experience.
    Skills: Python, JavaScript, React, Node.js, AWS.
    Experience: Led team of 5 engineers, delivered 3 production systems.
    Education: BS Computer Science, MIT."""
    
    job = """Full Stack Developer role requiring:
    - Python expertise for backend development
    - React and modern JavaScript frameworks
    - Cloud experience (AWS preferred)
    - Leadership capabilities
    - 3+ years professional experience"""
    
    # Test match analysis
    print("\n1. Testing match analysis...")
    match = analyze_match(resume, job)
    score = match['overall_score']
    assert score >= 0, f"Invalid score: {score}"
    print(f"   Match score: {score}%")
    
    # Test tailoring
    print("\n2. Testing resume tailoring...")
    tailored = tailor_resume(resume, job, match)
    assert len(tailored) > 100, f"Tailored resume too short: {len(tailored)}"
    print(f"   Tailored resume length: {len(tailored)} chars")
    
    # Test cover letter
    print("\n3. Testing cover letter generation...")
    letter = generate_cover_letter(resume, job, match)
    assert len(letter) > 100, f"Cover letter too short: {len(letter)}"
    print(f"   Cover letter length: {len(letter)} chars")
    
    print("\n=== ALL TESTS PASSED ===")
    return True

if __name__ == "__main__":
    try:
        test_ai_integration()
        sys.exit(0)
    except Exception as e:
        print(f"\n=== TEST FAILED ===")
        print(f"Error: {e}")
        sys.exit(1)

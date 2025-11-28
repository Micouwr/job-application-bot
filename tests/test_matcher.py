"""
Tests for the Matcher class implementation (keyword overlap scoring).
This suite verifies that the tokenization, scoring, and ranking logic work as expected.
"""

import pytest

# Import the correct class name from the assumed package structure
from app.matcher import Matcher

@pytest.fixture
def matcher():
    """Returns a Matcher instance for testing."""
    return Matcher()

def test_tokenize_cleans_and_filters_stopwords(matcher):
    """
    Test that the tokenizer handles punctuation, lowercasing, and correctly filters stopwords.
    """
    text = "The quick brown fox, said JUMP! Python is required. SQL."
    expected_tokens = ["quick", "brown", "fox", "said", "jump", "python", "required", "sql"]
    
    tokens = matcher._tokenize(text)
    
    # Check that the final set of tokens is correct, regardless of internal order
    assert sorted(tokens) == sorted(expected_tokens)
    assert "the" not in tokens  # Stopword check
    assert "is" not in tokens   # Stopword check
    assert "fox," not in tokens # Punctuation check
    assert "JUMP!" not in tokens # Punctuation check

def test_score_resume_perfect_match(matcher):
    """Tests a perfect keyword overlap, resulting in a score near 1.0."""
    job_text = "The role requires Python and AWS experience."
    resume_text = "My main skills are Python and AWS."
    
    score = matcher.score_resume_for_job(resume_text, job_text)
    
    # A high overlap should push the sigmoid-scaled score close to 1.0
    assert score > 0.95

def test_score_resume_partial_match(matcher):
    """Tests a partial keyword match."""
    job_text = "Required skills: Python, SQL, Cloud Architecture."
    resume_text = "I know Python and have SQL knowledge."
    
    score = matcher.score_resume_for_job(resume_text, job_text)
    
    # This should be a mid-to-high score, confirming partial overlap is measured
    assert score > 0.6 and score < 0.9

def test_score_resume_no_match(matcher):
    """Tests zero keyword overlap."""
    job_text = "Requires Rust and Haskell."
    resume_text = "I only know Python and Java."
    
    score = matcher.score_resume_for_job(resume_text, job_text)
    
    # Zero overlap should result in a score very close to 0.0
    assert score < 0.05

def test_score_resume_empty_text(matcher):
    """Tests scoring when one or both inputs are empty."""
    score1 = matcher.score_resume_for_job("", "job text")
    score2 = matcher.score_resume_for_job("resume text", "")
    score3 = matcher.score_resume_for_job("", "")
    
    assert score1 == 0.0
    assert score2 == 0.0
    assert score3 == 0.0

def test_top_matches_ordering_and_limit(matcher):
    """Tests that top_matches correctly sorts results by score descending and respects the limit."""
    job_text = "We need Python, SQL, and DevOps."
    resumes = {
        "r1.txt": "I know Python, SQL, and DevOps.",  # Highest score
        "r2.txt": "I only know Python.",             # Medium score
        "r3.txt": "I am a Java expert.",             # Lowest score
    }
    
    # Requesting the top 2 matches
    results = matcher.top_matches(resumes, job_text, top_n=2)
    
    assert len(results) == 2
    # Check that r1 is the top match (index 0)
    assert results[0][0] == "r1.txt"
    # Check that r2 is the second match (index 1)
    assert results[1][0] == "r2.txt"
    # Ensure scores are correctly ordered
    assert results[0][1] > results[1][1]
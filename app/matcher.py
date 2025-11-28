from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

# Simple list of English stopwords for basic text cleaning.
# This helps focus the matching on relevant keywords (skills, titles, etc.).
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "about", "above", "across", "after",
    "against", "along", "amid", "among", "around", "at", "before", "behind",
    "below", "beneath", "beside", "between", "beyond", "by", "down", "during",
    "except", "for", "from", "in", "inside", "into", "like", "near", "of",
    "off", "on", "onto", "out", "outside", "over", "through", "to", "under",
    "up", "upon", "with", "within", "without", "is", "am", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "as",
    "no", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "can", "will", "just", "don", "should", "now"
}


class Matcher:
    """
    Simple resume <-> job matcher.

    This module contains a lightweight scoring function which you can replace or
    extend with a more advanced algorithm (semantic matching using embeddings, etc).
    """

    def __init__(self) -> None:
        # Placeholder for any initialization (e.g., loaded models)
        pass

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize the text, remove punctuation, lowercase, and filter stopwords.
        """
        # 1. Replace all non-alphanumeric characters (except spaces) with a space
        text = re.sub(r'[^\w\s]', ' ', text)
        # 2. Split, lowercase, and filter stopwords
        tokens = []
        for t in text.split():
            token = t.lower()
            # Filter out empty strings and stopwords
            if token and token not in STOPWORDS:
                tokens.append(token)
        return tokens

    def score_resume_for_job(self, resume_text: str, job_text: str) -> float:
        """
        Produce a match score between 0.0 and 1.0 based on keyword overlap.

        The current implementation is a normalized overlap of word tokens (after
        removing stopwords and punctuation) with inverse-length scaling to avoid
        short-text bias.

        Args:
            resume_text: plain text of resume
            job_text: plain text of job description

        Returns:
            float between 0 and 1 (higher = better match)
        """
        r_tokens = set(self._tokenize(resume_text))
        j_tokens = set(self._tokenize(job_text))

        if not r_tokens or not j_tokens:
            return 0.0

        # Calculate overlap
        intersect = r_tokens.intersection(j_tokens)

        # Raw score: Intersection size divided by the total number of job tokens.
        # This measures what percentage of the job requirements are covered by the resume.
        raw_score = len(intersect) / max(len(j_tokens), 1)

        # Final score: Normalize the raw score (0 to 1) using a Sigmoid function
        # to produce a smoother, non-linear score between ~0.0 and ~1.0.
        return 1.0 / (1.0 + math.exp(-6 * (raw_score - 0.25)))

    def top_matches(
        self, resumes: Dict[str, str], job_text: str, top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Score multiple resumes and return top N matches.

        Args:
            resumes: mapping from resume_id (or filename) to resume text
            job_text: job description text
            top_n: how many top results to return

        Returns:
            list of (resume_id, score) sorted by score descending
        """
        scores = []
        for rid, text in resumes.items():
            score = self.score_resume_for_job(text, job_text)
            scores.append((rid, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]
# app/matcher.py
from __future__ import annotations

import math
from typing import Dict, List, Tuple


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
        return [t.lower() for t in text.split() if t.strip()]

    def score_resume_for_job(self, resume_text: str, job_text: str) -> float:
        """
        Produce a simple match score between 0.0 and 1.0.

        The current implementation is a normalized overlap of word tokens with
        inverse-length scaling to avoid short-text bias.

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
        intersect = r_tokens.intersection(j_tokens)
        raw_score = len(intersect) / max(len(j_tokens), 1)
        # normalize with logistic scaling for smoother values
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

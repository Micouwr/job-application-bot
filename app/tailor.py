# app/tailor.py
from __future__ import annotations
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)


class APIClient:
    """
    Small wrapper placeholder for AI API calls (Anthropic/OpenAI/etc).

    Replace `call_model` implementation with your project's actual API integration.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def call_model(self, prompt: str) -> str:
        """
        Synchronous model call. Implement retries, timeouts, and parsing here.

        Currently returns a placeholder echo. Replace with your API call.
        """
        # Basic retry pattern (2 retries)
        retries = 2
        for attempt in range(1, retries + 2):
            try:
                # TODO: replace this block with actual API call (requests/httpx/official SDK)
                logger.debug("APIClient.call_model attempt %s", attempt)
                time.sleep(0.2)  # simulate latency
                # Return a placeholder trimmed to simulate "tailoring"
                return f"[TAILORED VERSION - attempt {attempt}]\n\n{prompt[:400]}..."
            except Exception as exc:
                logger.exception("Model call failed on attempt %s: %s", attempt, exc)
                if attempt > retries:
                    raise
                time.sleep(1.0 * attempt)
        raise RuntimeError("unreachable")


class Tailor:
    """
    Tailor service: given resume text and job description, produce a tailored resume.

    Use an APIClient implementation (or local model) to perform the transformation.
    """

    def __init__(self, api_client: Optional[APIClient] = None) -> None:
        self.client = api_client or APIClient()

    def tailor_resume(self, resume_text: str, job_text: str) -> str:
        """
        Return a tailored resume for the given job description.

        This method creates a prompt combining resume and job text and sends it
        to the model. If you have a constrain of "do not invent facts", ensure
        you instruct the model accordingly in the prompt.

        Args:
            resume_text: original resume
            job_text: target job description

        Returns:
            tailored resume text
        """
        prompt = (
            "You are a resume assistant. Rewrite the resume to emphasize skills and "
            "experience that match the following job description. Do not invent new "
            "facts; only rephrase and reorder content present in the resume.\n\n"
            "JOB DESCRIPTION:\n"
            f"{job_text}\n\n"
            "RESUME:\n"
            f"{resume_text}\n\n"
            "Produce a tailored resume. Use bullet points where appropriate."
        )
        result = self.client.call_model(prompt)
        return result
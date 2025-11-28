from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class APIClient:
    """
    Small wrapper placeholder for AI API calls (Anthropic/OpenAI/Gemini/etc).

    It includes basic retry logic and placeholders for LLM configuration parameters.
    Replace `call_model` implementation with your project's actual API integration.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        model_name: str = "gemini-2.5-flash",  # Placeholder model name
        temperature: float = 0.7,  # Controls creativity/randomness (0.0=deterministic)
    ) -> None:
        # In a real app, the API key might be loaded from an environment variable
        # by the SDK, but we keep it here for transparency.
        self.api_key = api_key
        self.timeout = timeout
        self.model_name = model_name
        self.temperature = temperature
        logger.debug("APIClient initialized with model: %s, temperature: %s", self.model_name, self.temperature)

    def call_model(self, prompt: str) -> str:
        """
        Synchronous model call. Implement retries, timeouts, and parsing here.

        Currently returns a placeholder echo. Replace with your API call.
        """
        # Basic retry pattern with exponential backoff simulation
        retries = 2
        for attempt in range(1, retries + 2):
            try:
                # --- ACTUAL API CALL BLOCK STARTS HERE ---
                # TODO: replace this block with actual API call (requests/httpx/official SDK)
                logger.debug(
                    "APIClient.call_model attempt %s (using %s, temp=%.1f)",
                    attempt, self.model_name, self.temperature
                )
                time.sleep(0.2 * attempt)  # Simulate latency with slight backoff

                # Return a placeholder trimmed to simulate a result
                return (
                    f"[TAILORED by {self.model_name}, temp={self.temperature}, attempt {attempt}]\n\n"
                    f"{prompt[:400].strip()}..."
                )
                # --- ACTUAL API CALL BLOCK ENDS HERE ---

            except Exception as exc:
                # Log the error, which is crucial for debugging production issues
                logger.exception("Model call failed on attempt %s: %s", attempt, exc)
                if attempt > retries:
                    raise  # Re-raise the exception if retries are exhausted
                time.sleep(1.0 * attempt) # Wait longer before the next retry
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
        to the model. It includes clear instructions to ensure the model focuses
        on relevant details and avoids making up new facts.

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
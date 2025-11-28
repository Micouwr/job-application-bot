from __future__ import annotations

import logging
import time
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class APIClient:
    """
    Small wrapper placeholder for AI API calls (Anthropic/OpenAI/Gemini/etc).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.7,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.model_name = model_name
        self.temperature = temperature
        logger.debug("APIClient initialized with model: %s, temperature: %s", self.model_name, self.temperature)

    def call_model(self, prompt: str) -> str:
        """
        Synchronous model call. Implement retries, timeouts, and parsing here.
        """
        retries = 2
        for attempt in range(1, retries + 2):
            try:
                # --- Placeholder API CALL ---
                logger.debug(
                    "APIClient.call_model attempt %s (using %s, temp=%.1f)",
                    attempt, self.model_name, self.temperature
                )
                time.sleep(0.2 * attempt)
                
                # Placeholder response simulating structured LLM output
                mock_text = (
                    f"[START_RESUME]I used my Python and SQL skills to drive 20%% efficiency gains, "
                    f"a fact now strongly emphasized in this tailored resume.[END_RESUME]\n"
                    f"[START_COVER_LETTER]Dear Hiring Manager, I am writing to express my strong interest in the role...[END_COVER_LETTER]\n"
                    f"[START_CHANGES]1. Emphasized Python/SQL synergy.\n2. Added quantitative result (20%%).\n3. Re-ordered sections to prioritize matching keywords.[END_CHANGES]"
                )
                return mock_text
                # --- End Placeholder ---

            except Exception as exc:
                logger.exception("Model call failed on attempt %s: %s", attempt, exc)
                if attempt > retries:
                    raise
                time.sleep(1.0 * attempt)
        raise RuntimeError("unreachable")


class ResumeTailor:
    """
    Tailor service: given resume text and job description, produces a tailored application package.
    """

    def __init__(self, api_client: Optional[APIClient] = None) -> None:
        self.client = api_client or APIClient()

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parses the model's structured response (using custom tags) into a dictionary.
        
        Raises:
            ValueError: If mandatory tags are missing, indicating a malformed response.
        """
        result = {}
        
        tags = {
            "RESUME": "resume_text",
            "COVER_LETTER": "cover_letter",
            "CHANGES": "changes",
        }

        # Check for mandatory tags (as per your test case logic)
        if "[START_RESUME]" not in response or "[END_RESUME]" not in response:
             raise ValueError("Malformed AI response: Missing mandatory [RESUME] tags.")

        for tag, key in tags.items():
            start_tag = f"[START_{tag}]"
            end_tag = f"[END_{tag}]"
            
            # Use regex to safely extract content between the tags, using DOTALL for multi-line content
            match = re.search(f"{re.escape(start_tag)}(.*?){re.escape(end_tag)}", response, re.DOTALL)
            
            content = match.group(1).strip() if match else ""

            if key == "changes":
                # Split changes into a list, filtering out empty lines
                result[key] = [c.strip() for c in content.split('\n') if c.strip()]
            else:
                result[key] = content

        return result


    def tailor_application(self, resume_text: str, job_text: str) -> Dict[str, Any]:
        """
        Returns a tailored application package (resume, cover letter, changes)
        for the given job description.
        """
        prompt = (
            "You are a professional application writer. Based on the RESUME and JOB DESCRIPTION, "
            "rewrite the resume and generate a concise cover letter (max 3 paragraphs). "
            "Also, list all major changes made to the original resume using a numbered list.\n"
            "Constraint: Do not invent new facts; only rephrase content present in the resume.\n\n"
            
            "**OUTPUT FORMAT (MANDATORY):**\n"
            "You MUST use the following structured format EXACTLY, including all tags:\n\n"
            "[START_RESUME]\n<Tailored resume text>\n[END_RESUME]\n\n"
            "[START_COVER_LETTER]\n<Generated cover letter>\n[END_COVER_LETTER]\n\n"
            "[START_CHANGES]\n<Change 1>\n<Change 2>\n[END_CHANGES]\n\n"

            "JOB DESCRIPTION:\n"
            f"{job_text}\n\n"
            "RESUME:\n"
            f"{resume_text}"
        )
        
        raw_result = self.client.call_model(prompt)
        
        # Use the structured parsing method to return the final application package
        return self._parse_response(raw_result)
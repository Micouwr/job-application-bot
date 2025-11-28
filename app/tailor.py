from __future__ import annotations

import logging
import time
import re
import requests
import json
from typing import Optional, Dict, Any, List

from .config import config

logger = logging.getLogger(__name__)


class APIClient:
    """
    Client for interacting with the Gemini API for content generation.
    
    Implements exponential backoff and enables Google Search grounding
    for access to real-time information.
    """
    
    # Base URL for the non-streaming generateContent endpoint
    # NOTE: Using the -preview model which supports the Google Search tool.
    API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = config.GEMINI_API_KEY,
        timeout: int = 30,
        # Ensure the model used supports search grounding
        model_name: str = "gemini-2.5-flash-preview-09-2025", 
        temperature: float = config.LLM_TEMPERATURE,
    ) -> None:
        self.api_key = api_key
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not set. API calls will fail.")
            
        self.timeout = timeout
        self.model_name = model_name
        self.temperature = temperature
        logger.info("APIClient initialized with model: %s (Search Grounding Enabled)", self.model_name)

    def _prepare_payload(self, prompt: str) -> Dict[str, Any]:
        """Constructs the request payload for the Gemini API, enabling search grounding."""
        return {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            # 1. Add tools property to enable Google Search grounding
            "tools": [{"google_search": {}}],
            
            "config": {
                "temperature": self.temperature,
            }
        }

    def call_model(self, prompt: str) -> str:
        """
        Calls the Gemini API, handling retries with exponential backoff.
        
        Returns:
            The raw text response from the model.
        
        Raises:
            RuntimeError: If the API call fails after all retries.
        """
        if not self.api_key:
            raise RuntimeError("Cannot call API: GEMINI_API_KEY is missing.")

        api_url = f"{self.API_BASE_URL}/{self.model_name}:generateContent?key={self.api_key}"
        payload = self._prepare_payload(prompt)
        headers = {"Content-Type": "application/json"}
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug("API call attempt %s to %s (with search grounding)", attempt, self.model_name)
                
                response = requests.post(
                    api_url, 
                    headers=headers, 
                    data=json.dumps(payload),
                    timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()
                
                # Extract the text content
                candidate = data.get("candidates", [])[0]
                text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
                
                if text:
                    # Log grounding sources if present (optional but good practice)
                    grounding = candidate.get("groundingMetadata", {}).get("groundingAttributions", [])
                    if grounding:
                        sources = [a.get("web", {}).get("title", "Untitled Source") for a in grounding]
                        logger.info("Search grounding used. Sources found: %s", ", ".join(sources))
                        
                    return text
                else:
                    logger.warning("API returned success but text field was empty.")
                    raise RuntimeError("Empty text returned from model.")

            except requests.exceptions.RequestException as exc:
                is_retryable = response.status_code in [429, 500, 503] if 'response' in locals() else True
                
                if attempt < max_attempts and is_retryable:
                    delay = 2**attempt
                    logger.warning("API call failed (Attempt %s/%s). Retrying in %s seconds. Error: %s", 
                                   attempt, max_attempts, delay, exc)
                    time.sleep(delay)
                else:
                    logger.error("API call failed permanently after %s attempts. Error: %s", max_attempts, exc)
                    raise RuntimeError(f"Failed to call Gemini API after {max_attempts} attempts.") from exc
            
            except Exception as exc:
                logger.error("Unexpected error during API call: %s", exc)
                raise RuntimeError("Unexpected error processing API response.") from exc
        
        raise RuntimeError("Model call logic flow error.")


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

        # Check for mandatory tags
        if "[START_RESUME]" not in response or "[END_RESUME]" not in response:
             raise ValueError("Malformed AI response: Missing mandatory [RESUME] tags.")

        for tag, key in tags.items():
            start_tag = f"[START_{tag}]"
            end_tag = f"[END_{tag}]"
            
            # Use regex to safely extract content between the tags
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
            "The cover letter MUST be personalized by referencing the company's recent news, "
            "achievements, or mission, leveraging your ability to search the web for current context. "
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
        
        return self._parse_response(raw_result)
from pathlib import Path
import re
import json
import logging
from typing import Any
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import google.generativeai as genai

# Locked to Gemini 2.5 Flash - current best balance of speed + quality
GEMINI_MODEL = "gemini-2.5-flash"

logger = logging.getLogger(__name__)

class PromptManager:
    def __init__(self):
        # Absolute path - works no matter where script is run from
        prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
        if not prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")

        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def load(self, name: str) -> Any:
        try:
            return self.env.get_template(f"{name}.jinja2")
        except TemplateNotFound as e:
            raise FileNotFoundError(f"Prompt template not found: prompts/{name}.jinja2") from e

    def system(self) -> str:
        path = Path(__file__).resolve().parent.parent / "prompts" / "system.txt"
        if not path.exists():
            raise FileNotFoundError(f"System prompt missing: {path}")
        return path.read_text(encoding="utf-8").strip()

    def system_senior(self) -> str:
        path = Path(__file__).resolve().parent.parent / "prompts" / "system_senior.txt"
        if not path.exists():
            raise FileNotFoundError(f"Senior system prompt missing: {path}")
        return path.read_text(encoding="utf-8").strip()

    def extract_skills(self, job_description: str) -> list:
        template = self.load("skill_extraction")
        prompt_text = template.render(job_description=job_description)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt_text)
        text = response.text.strip()

        # Robustly remove any markdown code fences (with or without "json" label)
        text = re.sub(r"^```(?:json)?\s*\n|```$", "", text, flags=re.MULTILINE).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse skills JSON: {e}\nRaw output: {text[:500]}")
            return []  # Safe empty list - prevents crashes

    def generate(self, prompt: str, senior_voice: bool = False) -> str:
        system_text = self.system_senior() if senior_voice else self.system()
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_text
        )
        response = model.generate_content(prompt)
        return response.text

# Global instance used everywhere
prompts = PromptManager()
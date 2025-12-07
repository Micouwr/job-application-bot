from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import json
import google.generativeai as genai

# Locked to Gemini 2.5 Flash - current best balance of speed + quality
GEMINI_MODEL = "gemini-2.5-flash"

class PromptManager:
    def __init__(self):
        prompts_dir = Path(__file__).parent.parent / "prompts"
        self.env = Environment(loader=FileSystemLoader(prompts_dir), trim_blocks=True, lstrip_blocks=True)

    def load(self, name: str):
        return self.env.get_template(f"{name}.jinja2")

    def system(self) -> str:
        return (Path(__file__).parent.parent / "prompts" / "system.txt").read_text().strip()

    def system_senior(self) -> str:
        return (Path(__file__).parent.parent / "prompts" / "system_senior.txt").read_text().strip()

    def extract_skills(self, job_description: str):
        template = self.load("skill_extraction")
        prompt = template.render(job_description=job_description)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)

    def generate(self, prompt: str, senior_voice: bool = False):
        system = self.system_senior() if senior_voice else self.system()
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system
        )
        return model.generate_content(prompt).text

# Global instance used everywhere
prompts = PromptManager()
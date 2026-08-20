import os
from pathlib import Path
import yaml
import instructor
from openai import OpenAI

class LocalLLM:
    def __init__(self, model=None):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.api_key = os.getenv("OLLAMA_API_KEY", "ollama")
        config = yaml.safe_load(Path("config/models.yaml").read_text(encoding="utf-8"))
        self.model = model or os.getenv("OLLAMA_MODEL") or config["default_model"]
        self.client = instructor.from_openai(
            OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=180),
            mode=instructor.Mode.JSON,
        )

    def structured(self, response_model, system, user):
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=response_model,
            extra_body={"options": {"temperature": 0, "num_ctx": 16384}},
        )

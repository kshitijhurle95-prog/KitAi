"""Local Ollama client for zero-cost, private offline inference."""
import httpx
from typing import List, Dict, Any, Optional
from app.config import settings
from app.utils.logger import logger


class OllamaClient:
    """Async client communicating with local Ollama daemon."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.default_model = settings.OLLAMA_MODEL

    async def is_available(self) -> bool:
        """Check if local Ollama server is responding."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """Sends chat request to Ollama endpoint."""
        chosen_model = model or self.default_model
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": chosen_model,
                    "messages": messages,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                    "stream": False,
                }
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]


ollama_client = OllamaClient()

"""Groq client wrapper with rate limiting, error handling, and multimodal support."""
import asyncio
import time
from collections import deque
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from app.config import settings
from app.utils.logger import logger


class GroqClientWrapper:
    """Async wrapper around Groq API with rate limiting and exponential backoff."""

    def __init__(self):
        self._client: Optional[AsyncGroq] = None
        self._request_times: deque[float] = deque()
        self._rpm = settings.GROQ_RPM

    @property
    def client(self) -> AsyncGroq:
        if self._client is None:
            self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return self._client

    async def _wait_for_rate_limit(self):
        """Enforces requests per minute limit."""
        now = time.monotonic()
        while self._request_times and self._request_times[0] < now - 60:
            self._request_times.popleft()

        if len(self._request_times) >= self._rpm:
            wait_time = 60.0 - (now - self._request_times[0])
            if wait_time > 0:
                logger.warning(f"Groq rate limit approaching. Throttling for {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._request_times.append(time.monotonic())

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_placeholder"))

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 800,
        stream: bool = False
    ) -> Any:
        """Sends chat completion to Groq with rate-limit protection."""
        if not self.is_configured():
            raise ValueError("GROQ_API_KEY is not configured. Please set your key in .env")

        await self._wait_for_rate_limit()

        chosen_model = model or settings.GROQ_MODEL
        # Cap max_tokens at 950 to stay under Groq free tier OTPM limits
        safe_max_tokens = min(max_tokens or 800, 950)

        try:
            response = await self.client.chat.completions.create(
                model=chosen_model,
                messages=messages,
                temperature=temperature,
                max_tokens=safe_max_tokens,
                stream=stream
            )
            if stream:
                return response
            return response.choices[0].message.content
        except Exception as e:
            err_str = str(e).lower()
            if "reduce max_tokens" in err_str or "output tokens per minute" in err_str or "rate_limit_exceeded" in err_str:
                logger.warning(f"Groq OTPM limit hit, retrying with max_tokens=500...")
                try:
                    response = await self.client.chat.completions.create(
                        model=chosen_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=500,
                        stream=stream
                    )
                    if stream:
                        return response
                    return response.choices[0].message.content
                except Exception as retry_err:
                    logger.error(f"Groq retry with 500 tokens also failed: {retry_err}")
                    raise retry_err
            logger.error(f"Groq chat failed with model '{chosen_model}': {e}")
            raise

    async def chat_with_vision(
        self,
        prompt_text: str,
        image_base64: str,
        mime_type: str = "image/jpeg",
        model: Optional[str] = None
    ) -> str:
        """Sends an image + text prompt to vision model."""
        if not self.is_configured():
            raise ValueError("GROQ_API_KEY is not configured.")

        await self._wait_for_rate_limit()
        vision_model = model or settings.GROQ_VISION_MODEL

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        response = await self.client.chat.completions.create(
            model=vision_model,
            messages=messages,
            max_tokens=2048
        )
        return response.choices[0].message.content

    async def transcribe(self, audio_file_path: str) -> str:
        """Transcribe an audio file using Groq's Whisper."""
        if not self.is_configured():
            raise ValueError("GROQ_API_KEY is not configured.")

        await self._wait_for_rate_limit()
        with open(audio_file_path, "rb") as f:
            transcription = await self.client.audio.transcriptions.create(
                model=settings.GROQ_WHISPER_MODEL,
                file=f,
                response_format="text"
            )
        return str(transcription)


groq_client = GroqClientWrapper()

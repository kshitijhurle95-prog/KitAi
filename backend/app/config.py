"""Application configuration loaded from environment variables."""
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # === API Keys ===
    GROQ_API_KEY: str = "gsk_placeholder_replace_with_your_key"

    # === Database ===
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/studybrain.db"

    # === LLM Settings ===
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_VISION_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # === Paths ===
    DATA_DIR: Path = BACKEND_DIR / "data"
    CHROMA_DIR: Path = BACKEND_DIR / "data" / "chroma"
    VIDEOS_DIR: Path = BACKEND_DIR / "data" / "videos"
    AUDIO_DIR: Path = BACKEND_DIR / "data" / "audio"
    IMAGES_DIR: Path = BACKEND_DIR / "data" / "images"
    UPLOADS_DIR: Path = BACKEND_DIR / "data" / "uploads"

    # === TTS ===
    TTS_ENGINE: str = "edge"  # edge | kokoro | google
    TTS_LANGUAGE: str = "en"  # en | hi
    TTS_VOICE: str = "en-US-AriaNeural"

    # === Rate Limiting ===
    GROQ_RPM: int = 30
    GROQ_TPM: int = 6000

    # === App ===
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=[ROOT_DIR / ".env", BACKEND_DIR / ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

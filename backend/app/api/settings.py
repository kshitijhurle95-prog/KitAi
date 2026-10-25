"""Settings and API Configuration endpoints with dynamic Groq model discovery."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.config import settings, ROOT_DIR, BACKEND_DIR
from app.services.groq_client import groq_client
from app.memory.vector_store import vector_store
from app.utils.logger import logger

router = APIRouter()


class SettingsUpdateRequest(BaseModel):
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_language: Optional[str] = None


@router.get("/settings")
async def get_settings():
    """Retrieve current system configuration and dynamically discover Groq models."""
    raw_key = settings.GROQ_API_KEY
    has_key = bool(raw_key and not raw_key.startswith("gsk_placeholder"))

    masked_key = ""
    if has_key:
        masked_key = raw_key[:4] + "••••••••••••" + raw_key[-4:] if len(raw_key) > 8 else "••••••••"

    # Default fallback models
    available_models = [
        {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B (Fast, Highly Recommended)", "desc": "Optimal coding & academic reasoning"},
        {"id": "openai/gpt-oss-120b", "name": "OpenAI GPT-OSS 120B (Deep Reasoning)", "desc": "Complex theoretical breakdowns"},
        {"id": "openai/gpt-oss-20b", "name": "OpenAI GPT-OSS 20B (Fast)", "desc": "Lightweight sub-second responses"}
    ]

    # If API key is present, query user's actual models from Groq dynamically!
    if has_key:
        try:
            m_list = await groq_client.client.models.list()
            chat_models = []
            for m in m_list.data:
                mid = m.id
                # Filter to conversational text models
                if any(k in mid for k in ["qwen", "gpt-oss", "llama", "mixtral", "gemma", "allam"]):
                    chat_models.append({
                        "id": mid,
                        "name": mid,
                        "desc": "Active model on your Groq key"
                    })
            if chat_models:
                available_models = chat_models
        except Exception as e:
            logger.warning(f"Could not fetch dynamic models: {e}")

    return {
        "has_api_key": has_key,
        "masked_api_key": masked_key,
        "groq_model": settings.GROQ_MODEL,
        "tts_voice": settings.TTS_VOICE,
        "tts_language": settings.TTS_LANGUAGE,
        "available_models": available_models,
        "available_voices": [
            {"id": "en-US-AriaNeural", "name": "Aria (US Female - Natural)", "lang": "en"},
            {"id": "en-US-GuyNeural", "name": "Guy (US Male - Clear)", "lang": "en"},
            {"id": "hi-IN-SwaraNeural", "name": "Swara (Hindi Female)", "lang": "hi"},
            {"id": "hi-IN-MadhurNeural", "name": "Madhur (Hindi Male)", "lang": "hi"}
        ]
    }


@router.post("/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Updates API key, models, and voice settings with persistent .env save."""
    test_status = "unchanged"

    # 1. Update GROQ API KEY if provided
    if req.groq_api_key is not None:
        clean_key = req.groq_api_key.strip()
        if clean_key:
            settings.GROQ_API_KEY = clean_key
            os.environ["GROQ_API_KEY"] = clean_key
            groq_client._client = None  # Reset client instance to reload new key

    # 2. Update Model & Voice
    if req.groq_model:
        settings.GROQ_MODEL = req.groq_model
        os.environ["GROQ_MODEL"] = req.groq_model
    if req.tts_voice:
        settings.TTS_VOICE = req.tts_voice
        os.environ["TTS_VOICE"] = req.tts_voice
    if req.tts_language:
        settings.TTS_LANGUAGE = req.tts_language
        os.environ["TTS_LANGUAGE"] = req.tts_language

    # 3. Test connection live against Groq with the selected model
    if groq_client.is_configured():
        try:
            target_model = settings.GROQ_MODEL or "qwen/qwen3.8-27b"
            await groq_client.chat(
                messages=[{"role": "user", "content": "ping"}],
                model=target_model,
                max_tokens=10
            )
            test_status = "connected"
            logger.info(f"Successfully connected to Groq API using model '{target_model}'.")
        except Exception as e:
            logger.warning(f"Groq API key test warning with model '{settings.GROQ_MODEL}': {e}")
            test_status = f"Key saved, but validation warning: {str(e)[:120]}"

    # 4. Persist to .env in both project root and backend dir
    for env_file in [ROOT_DIR / ".env", BACKEND_DIR / ".env"]:
        try:
            env_lines = []
            if env_file.exists():
                with open(env_file, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()

            keys_written = set()
            new_lines = []
            for line in env_lines:
                if line.startswith("GROQ_API_KEY="):
                    new_lines.append(f"GROQ_API_KEY={settings.GROQ_API_KEY}\n")
                    keys_written.add("GROQ_API_KEY")
                elif line.startswith("GROQ_MODEL="):
                    new_lines.append(f"GROQ_MODEL={settings.GROQ_MODEL}\n")
                    keys_written.add("GROQ_MODEL")
                elif line.startswith("TTS_VOICE="):
                    new_lines.append(f"TTS_VOICE={settings.TTS_VOICE}\n")
                    keys_written.add("TTS_VOICE")
                elif line.startswith("TTS_LANGUAGE="):
                    new_lines.append(f"TTS_LANGUAGE={settings.TTS_LANGUAGE}\n")
                    keys_written.add("TTS_LANGUAGE")
                else:
                    new_lines.append(line)

            if "GROQ_API_KEY" not in keys_written:
                new_lines.append(f"GROQ_API_KEY={settings.GROQ_API_KEY}\n")
            if "GROQ_MODEL" not in keys_written:
                new_lines.append(f"GROQ_MODEL={settings.GROQ_MODEL}\n")

            with open(env_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            logger.error(f"Error persisting .env to {env_file}: {e}")

    raw_key = settings.GROQ_API_KEY
    masked = raw_key[:4] + "••••••••••••" + raw_key[-4:] if len(raw_key) > 8 else "••••••••"

    return {
        "status": "success",
        "connection_test": test_status,
        "has_api_key": bool(raw_key and not raw_key.startswith("gsk_placeholder")),
        "masked_api_key": masked,
        "groq_model": settings.GROQ_MODEL,
        "tts_voice": settings.TTS_VOICE
    }


@router.post("/settings/clear-memory")
async def clear_memory():
    """Clears vector memory store for a fresh start."""
    try:
        vector_store._init_chroma()
        if vector_store._collection:
            vector_store._client.delete_collection("study_experiences_v2")
            vector_store._collection = None
            vector_store._init_chroma()
        return {"status": "cleared", "message": "Vector memory cleared successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""Multimodal upload and media processing endpoints."""
import shutil
import base64
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from app.config import settings
from app.services.groq_client import groq_client
from app.output.tts import generate_speech
from app.utils.logger import logger

router = APIRouter()


@router.post("/upload/audio")
async def upload_audio_endpoint(file: UploadFile = File(...)):
    """Accepts audio recording and transcribes it into text using Whisper."""
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = settings.UPLOADS_DIR / f"upload_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        if groq_client.is_configured():
            transcript = await groq_client.transcribe(str(temp_path))
            return {"transcript": transcript, "filename": file.filename}
        return {
            "transcript": "Audio received. Configure GROQ_API_KEY to enable Whisper STT transcription.",
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        temp_path.unlink(missing_ok=True)


@router.post("/upload/image")
async def upload_image_endpoint(
    file: UploadFile = File(...),
    prompt: str = Form("Describe this image in detail and extract any academic problems or code within it.")
):
    """Analyzes diagrams, charts, formulas, or homework images."""
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = settings.UPLOADS_DIR / f"upload_{file.filename}"

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        with open(temp_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")

        if groq_client.is_configured():
            analysis = await groq_client.chat_with_vision(
                prompt_text=prompt,
                image_base64=encoded_image,
                mime_type=file.content_type or "image/jpeg"
            )
            return {"analysis": analysis, "filename": file.filename}
        return {
            "analysis": "Image uploaded. Add GROQ_API_KEY to enable multimodal vision reasoning.",
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        temp_path.unlink(missing_ok=True)


@router.post("/tts")
async def tts_endpoint(text: str = Form(...), language: str = Form("en")):
    """Converts explanation text to an MP3 speech audio stream."""
    try:
        audio_path = await generate_speech(text, language=language)
        return FileResponse(
            path=str(audio_path),
            media_type="audio/mpeg",
            filename=audio_path.name
        )
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""Text-to-Speech synthesis using Edge-TTS (free, high quality, multi-language)."""
import uuid
from pathlib import Path
from typing import Optional
import edge_tts
from app.config import settings
from app.utils.logger import logger

VOICE_MAP = {
    "en": "en-US-AriaNeural",
    "en-male": "en-US-GuyNeural",
    "hi": "hi-IN-SwaraNeural",
    "hi-male": "hi-IN-MadhurNeural"
}


async def generate_speech(
    text: str,
    output_filename: Optional[str] = None,
    language: str = "en"
) -> Path:
    """
    Synthesize natural speech audio file from text.
    Returns the absolute Path of the generated audio file.
    """
    settings.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    clean_text = text.replace("```python", "").replace("```", "").strip()

    if len(clean_text) > 4000:
        clean_text = clean_text[:4000] + "..."

    filename = output_filename or f"speech_{uuid.uuid4().hex[:10]}.mp3"
    output_path = settings.AUDIO_DIR / filename
    voice = VOICE_MAP.get(language, settings.TTS_VOICE)

    try:
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(str(output_path))
        logger.info(f"Generated speech audio at {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise

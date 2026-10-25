"""Video Generation API endpoints."""
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.config import settings
from app.output.video_assembler import generate_animated_explainer_video
from app.utils.logger import logger

router = APIRouter()


class VideoGenerateRequest(BaseModel):
    topic: str = Field(..., description="Topic or concept to explain (e.g. 'Binary Search', 'Recursion')")
    context: Optional[str] = Field("", description="Optional solution or explanation text to guide narration")
    orientation: Optional[str] = Field("landscape", description="'landscape' (16:9) or 'portrait' (9:16 for Reels)")
    analogy_style: Optional[str] = Field("daily_life", description="Style of metaphor: 'daily_life', 'kitchen', 'traffic', 'school', 'sports'")


@router.post("/video/generate")
async def generate_video_endpoint(req: VideoGenerateRequest):
    """Generates an animated video explainer with voice-over narration and visual slides."""
    try:
        # Clean topic prefix if user entered a conversational prompt
        clean_topic = req.topic.strip()
        for prefix in [
            "generate an explainer video on", "generate an explainer video about",
            "create an explainer video on", "create a video on", "create a video about",
            "generate video on", "generate video for", "make a video on", "make a video about",
            "video on", "video about", "animate this", "animate", "explain"
        ]:
            if clean_topic.lower().startswith(prefix):
                clean_topic = clean_topic[len(prefix):].strip(" :,-")
                break
        clean_topic = clean_topic or req.topic

        logger.info(f"Generating explainer video for '{clean_topic}' (Orientation: {req.orientation}, Style: {req.analogy_style})...")
        result = await generate_animated_explainer_video(
            topic=clean_topic,
            context=req.context or "",
            orientation=req.orientation or "landscape",
            analogy_style=req.analogy_style or "daily_life"
        )
        return result
    except Exception as e:
        logger.error(f"Video generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@router.get("/video/list")
async def list_videos():
    """List all generated explainer videos available for playback."""
    settings.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    videos = []
    for f in settings.VIDEOS_DIR.glob("*.mp4"):
        videos.append({
            "name": f.name,
            "url": f"/media/videos/{f.name}",
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            "created_at": f.stat().st_ctime
        })
    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return {"videos": videos}

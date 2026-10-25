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


@router.post("/video/generate")
async def generate_video_endpoint(req: VideoGenerateRequest):
    """Generates an animated video explainer with voice-over narration and visual slides."""
    try:
        logger.info(f"Generating explainer video for '{req.topic}'...")
        result = await generate_animated_explainer_video(topic=req.topic, context=req.context)
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

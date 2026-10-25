"""StudyBrain - Main FastAPI entry point."""
import sys
import asyncio
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import create_tables
from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.api.memory import router as memory_router
from app.api.video import router as video_router
from app.api.settings import router as settings_router
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown hooks."""
    logger.info("Initializing StudyBrain Backend...")
    # Ensure all data directories exist
    for dir_path in [
        settings.DATA_DIR,
        settings.CHROMA_DIR,
        settings.VIDEOS_DIR,
        settings.AUDIO_DIR,
        settings.IMAGES_DIR,
        settings.UPLOADS_DIR,
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Initialize SQL tables
    await create_tables()
    logger.info("Database schemas verified.")

    yield
    logger.info("StudyBrain shutting down.")


app = FastAPI(
    title="StudyBrain API",
    description="Self-Learning Multimodal AI Study Agent Backend",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for generated audio and video files
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(settings.DATA_DIR)), name="media")

# Include API Routers
app.include_router(chat_router, prefix="/api", tags=["Chat & Learning"])
app.include_router(upload_router, prefix="/api", tags=["Multimodal Upload & TTS"])
app.include_router(memory_router, prefix="/api", tags=["Memory & Knowledge"])
app.include_router(video_router, prefix="/api", tags=["Animated Video Generation"])
app.include_router(settings_router, prefix="/api", tags=["Settings & Configuration"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": "StudyBrain Agent Backend",
        "version": "0.1.0",
        "database": "sqlite+aiosqlite",
        "tts_engine": settings.TTS_ENGINE,
        "default_llm": settings.GROQ_MODEL
    }

# Mount static web frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


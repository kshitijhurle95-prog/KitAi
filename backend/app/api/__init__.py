"""API router aggregator."""
from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.api.memory import router as memory_router

__all__ = ["chat_router", "upload_router", "memory_router"]

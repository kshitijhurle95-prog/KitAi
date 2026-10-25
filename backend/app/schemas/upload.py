"""Schemas for multimodal uploads."""
from typing import Optional
from pydantic import BaseModel


class AudioTranscribeResponse(BaseModel):
    transcript: str
    detected_language: Optional[str] = None
    duration: Optional[float] = None


class ImageAnalysisResponse(BaseModel):
    description: str
    extracted_text: Optional[str] = None
    problem_type: Optional[str] = None

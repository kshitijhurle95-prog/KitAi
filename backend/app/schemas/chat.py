"""Pydantic schemas for chat endpoints."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's query or code problem")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for tracking chat session")
    user_id: str = Field("default_user", description="Identifier for personalization")
    mode: str = Field("answer", description="Interaction mode: 'answer' | 'socratic' | 'explain'")
    image_base64: Optional[str] = Field(None, description="Optional base64-encoded image data")


class ChatResponse(BaseModel):
    reply: str
    solution: Optional[str] = None
    explanation: Optional[str] = None
    task_type: str
    code_output: Optional[str] = None
    code_passed: Optional[bool] = None
    conversation_id: str
    retrieved_memory: Optional[List[Dict[str, Any]]] = None


class FeedbackRequest(BaseModel):
    message_id: Optional[str] = None
    experience_id: Optional[str] = None
    query: str
    solution: str
    is_positive: bool
    notes: Optional[str] = None

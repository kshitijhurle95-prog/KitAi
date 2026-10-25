"""Chat and interaction endpoints."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import get_db
from app.models.conversation import Conversation, Message
from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest
from app.core.agent import study_agent
from app.utils.logger import logger

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Receives user query, runs agent pipeline, persists dialogue, and returns response."""
    conv_id = request.conversation_id or str(uuid.uuid4())

    # 1. Fetch or create conversation
    conv_stmt = select(Conversation).where(Conversation.id == conv_id)
    conv_res = await db.execute(conv_stmt)
    conv = conv_res.scalar_one_or_none()

    if conv is None:
        conv = Conversation(
            id=conv_id,
            user_id=request.user_id,
            title=request.message[:45] + ("..." if len(request.message) > 45 else "")
        )
        db.add(conv)
        await db.commit()

    # 2. Record user message
    user_msg = Message(
        conversation_id=conv_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    await db.commit()

    # 3. Retrieve recent history for context
    hist_stmt = (
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
    )
    hist_res = await db.execute(hist_stmt)
    history_records = hist_res.scalars().all()
    history_formatted = [
        {"role": m.role, "content": m.content}
        for m in history_records[-6:]
    ]

    # 4. Invoke Autonomous Study Agent
    try:
        agent_result = await study_agent.run(
            query=request.message,
            user_id=request.user_id,
            mode=request.mode,
            image_base64=request.image_base64,
            conversation_history=history_formatted
        )
    except Exception as e:
        logger.error(f"Error in study agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    # 5. Persist assistant reply
    assistant_msg = Message(
        conversation_id=conv_id,
        role="assistant",
        content=agent_result["reply"],
        task_type=agent_result.get("task_type"),
        solution=agent_result.get("solution"),
        explanation=agent_result.get("explanation"),
        code_output=agent_result.get("code_output"),
        code_passed=agent_result.get("code_passed"),
        metadata_json={
            "retrieved_memory_count": len(agent_result.get("retrieved_memory") or []),
            "video_url": agent_result.get("video_url")
        }
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        reply=agent_result["reply"],
        solution=agent_result.get("solution"),
        explanation=agent_result.get("explanation"),
        task_type=agent_result.get("task_type", "conceptual"),
        code_output=agent_result.get("code_output"),
        code_passed=agent_result.get("code_passed"),
        conversation_id=conv_id,
        video_url=agent_result.get("video_url"),
        retrieved_memory=agent_result.get("retrieved_memory")
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch all messages for a specific conversation session."""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    res = await db.execute(stmt)
    messages = res.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "task_type": m.task_type,
            "solution": m.solution,
            "explanation": m.explanation,
            "code_output": m.code_output,
            "code_passed": m.code_passed,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in messages
    ]

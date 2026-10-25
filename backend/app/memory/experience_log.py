"""Experience logger for persisting interactions and feedback."""
from typing import Optional, Dict, Any
from app.models import async_session
from app.models.experience import Experience
from app.memory.vector_store import vector_store
from app.utils.logger import logger


async def log_experience(
    query: str,
    solution: str,
    task_type: str,
    explanation: Optional[str] = None,
    success: bool = True,
    user_id: str = "default_user",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Logs the interaction to the relational DB and vector memory."""
    # 1. Save to relational DB
    exp_id = ""
    try:
        async with async_session() as session:
            exp = Experience(
                user_id=user_id,
                query=query,
                task_type=task_type,
                solution=solution,
                explanation=explanation,
                success=success,
                metadata_json=metadata or {}
            )
            session.add(exp)
            await session.commit()
            await session.refresh(exp)
            exp_id = exp.id
    except Exception as e:
        logger.error(f"Error saving experience to DB: {e}")

    # 2. Add to Vector Store for future semantic recall
    try:
        await vector_store.add_experience(
            query=query,
            solution=solution,
            user_id=user_id,
            task_type=task_type,
            success=success
        )
    except Exception as e:
        logger.error(f"Error indexing experience in vector store: {e}")

    return exp_id

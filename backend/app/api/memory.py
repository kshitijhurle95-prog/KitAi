"""Endpoints for querying memory, knowledge graph, and spaced repetition."""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.models import get_db
from app.models.flashcard import Flashcard
from app.memory.vector_store import vector_store
from app.memory.knowledge_graph import concept_graph
from app.memory.spaced_rep import calculate_next_review, FlashcardReviewData
from app.schemas.memory import MemorySearchResponse, ConceptMapResponse

router = APIRouter()


@router.get("/memory/search", response_model=MemorySearchResponse)
async def search_memory_endpoint(q: str = Query(..., description="Query text to search in memory")):
    """Searches vector store for past similar experiences."""
    results = await vector_store.search_similar(query=q, top_k=5)
    return MemorySearchResponse(query=q, results=results)


@router.get("/memory/graph", response_model=ConceptMapResponse)
async def get_concept_graph_endpoint(topic: str = Query("CS", description="Root topic")):
    """Returns the concept graph with nodes and dependency edges."""
    data = concept_graph.get_concept_subgraph(topic=topic, depth=2)
    return ConceptMapResponse(
        topic=data.get("topic", topic),
        nodes=data.get("nodes", []),
        edges=data.get("edges", [])
    )


@router.get("/flashcards/due")
async def get_due_flashcards(user_id: str = "default_user", db: AsyncSession = Depends(get_db)):
    """Fetch flashcards scheduled for review according to SM-2 spaced repetition."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Flashcard)
        .where(Flashcard.user_id == user_id, Flashcard.next_review <= now)
        .order_by(Flashcard.next_review)
    )
    res = await db.execute(stmt)
    cards = res.scalars().all()
    return [
        {
            "id": c.id,
            "topic": c.topic,
            "front": c.front,
            "back": c.back,
            "repetitions": c.repetitions,
            "interval_days": c.interval_days,
            "easiness": c.easiness
        }
        for c in cards
    ]

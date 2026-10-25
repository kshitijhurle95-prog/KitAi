"""Automated tests for StudyBrain core components."""
import pytest
import asyncio
from app.core.classifier import classify_task
from app.services.sandbox import execute_python_code
from app.memory.spaced_rep import calculate_next_review, FlashcardReviewData
from app.memory.knowledge_graph import concept_graph


@pytest.mark.asyncio
async def test_sandbox_execution():
    """Verify code sandbox runs clean code and catches errors."""
    code = "print(sum([1, 2, 3, 4, 5]))"
    res = await execute_python_code(code)
    assert res["passed"] is True
    assert "15" in res["output"]


@pytest.mark.asyncio
async def test_sandbox_syntax_error():
    """Verify syntax error capture."""
    bad_code = "def broken(:\n    pass"
    res = await execute_python_code(bad_code)
    assert res["passed"] is False
    assert res["error"] is not None


@pytest.mark.asyncio
async def test_classifier_heuristics():
    """Verify classification heuristics."""
    task = await classify_task("def quicksort(arr): return arr")
    assert task == "code"
    
    task_video = await classify_task("Create a video explaining Recursion with daily life analogy")
    assert task_video == "video"


def test_sm2_spaced_repetition():
    """Verify SM-2 algorithm advances intervals on high quality."""
    card = FlashcardReviewData(easiness=2.5, interval_days=1, repetitions=0)
    updated = calculate_next_review(card, quality=5)
    assert updated.repetitions == 1
    assert updated.interval_days == 1

    updated2 = calculate_next_review(updated, quality=5)
    assert updated2.repetitions == 2
    assert updated2.interval_days == 6


def test_knowledge_graph_traversal():
    """Verify concept graph holds default nodes."""
    prereqs = concept_graph.get_prerequisites("Recursion")
    assert isinstance(prereqs, list)

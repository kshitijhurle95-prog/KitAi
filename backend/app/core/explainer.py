"""Explanation engine supporting Socratic tutoring, analogies, and simplified breakdowns."""
from app.services.llm_router import llm_router
from app.utils.prompts import get_explainer_prompt
from app.utils.logger import logger


async def generate_explanation(
    query: str,
    solution: str,
    mode: str = "direct"
) -> str:
    """Generates an explanation adapted to the user's requested learning mode."""
    if mode == "answer":
        mode = "direct"

    template = get_explainer_prompt(mode)
    prompt = template.format(query=query, solution=solution)

    try:
        explanation = await llm_router.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048
        )
        return explanation
    except Exception as e:
        logger.error(f"Explanation generation failed: {e}")
        return solution

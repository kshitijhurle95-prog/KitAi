"""Solution verification and self-healing loop."""
from typing import Dict, Any, Tuple
from app.services.sandbox import execute_python_code, extract_python_code
from app.services.llm_router import llm_router
from app.utils.logger import logger


async def verify_and_heal_solution(
    solution: str,
    query: str,
    max_retries: int = 1
) -> Tuple[str, Dict[str, Any]]:
    """
    Checks if solution contains runnable code.
    If yes, runs it in sandbox. If code produces an error, prompts LLM to fix it.
    Returns:
        (healed_solution, verification_result)
    """
    code = extract_python_code(solution)
    if not code:
        return solution, {"passed": None, "output": None, "error": None}

    logger.info("Executing generated Python code in sandbox...")
    res = await execute_python_code(code)

    if res["passed"]:
        logger.info("Code verification passed.")
        return solution, res

    # Self-healing retry loop
    for attempt in range(max_retries):
        logger.warning(f"Code verification failed on attempt {attempt+1}. Self-healing...")
        fix_prompt = (
            f"The following code generated for the user's query failed during execution.\n\n"
            f"User Query: {query}\n\n"
            f"Code:\n```python\n{code}\n```\n\n"
            f"Execution Error/Output:\n{res.get('error') or res.get('output')}\n\n"
            f"Please diagnose the error, fix the bug, and provide the corrected complete code solution."
        )

        try:
            fixed_solution = await llm_router.chat(
                messages=[{"role": "user", "content": fix_prompt}],
                temperature=0.1,
                max_tokens=4096
            )
            fixed_code = extract_python_code(fixed_solution)
            if fixed_code:
                new_res = await execute_python_code(fixed_code)
                if new_res["passed"]:
                    logger.info("Self-healing successful! Code verified.")
                    return fixed_solution, new_res
                res = new_res
        except Exception as e:
            logger.error(f"Error during self-healing: {e}")
            break

    return solution, res

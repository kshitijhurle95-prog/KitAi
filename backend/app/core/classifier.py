"""Intent classifier module for routing study requests."""
from app.services.llm_router import llm_router
from app.utils.prompts import CLASSIFIER_PROMPT
from app.utils.logger import logger

VALID_TASK_TYPES = {"code", "math", "conceptual", "factual", "explain", "conversational", "video"}


async def classify_task(query: str) -> str:
    """Classifies user query into task type using heuristic fast-path or LLM."""
    query_lower = query.strip().lower()

    # 1. Fast heuristics: Video requests
    video_triggers = [
        "create a video", "create video", "generate video", "make a video",
        "explainer video", "animated video", "video on", "video explaining",
        "video about", "create a reel", "make a reel", "animate this",
        "concept in motion", "generate animated video"
    ]
    if any(vt in query_lower for vt in video_triggers):
        return "video"

    # 2. Fast heuristics: Greetings and casual chat
    greetings = {"hi", "hello", "hey", "hola", "yo", "sup", "good morning", "good afternoon", "good evening", "how are you", "who are you", "what can you do"}
    if query_lower in greetings or any(query_lower.startswith(g + " ") for g in ["hi", "hello", "hey"]):
        return "conversational"

    # 2. Fast heuristics: Gibberish or repeated single keys (e.g. "hhhhhhhhhhhh")
    alnum_only = "".join(c for c in query_lower if c.isalnum())
    if len(alnum_only) >= 3 and len(set(alnum_only)) <= 2:
        return "conversational"

    # 3. Fast heuristics: Explicit code requests or actual code syntax
    code_triggers = [
        "write code", "solve in c++", "code in c++", "code in python", "code in java",
        "in javascript", "write a function", "implement a function", "fix this error",
        "syntaxerror", "traceback", "write a program", "coding problem", "leetcode",
        "def ", "#include", "int main", "public static void", "cout <<", "return "
    ]
    if any(kw in query_lower for kw in code_triggers):
        return "code"

    # 4. Fast heuristics: Math
    if any(kw in query_lower for kw in ["solve equation", "integral", "derivative", "calculate", "sum of", "dx"]):
        return "math"

    prompt = CLASSIFIER_PROMPT.format(query=query)
    try:
        response = await llm_router.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=20
        )
        task_type = response.strip().lower().replace('"', '').replace("'", "").replace(".", "")
        for valid in VALID_TASK_TYPES:
            if valid in task_type:
                return valid
        return "conversational"
    except Exception as e:
        logger.warning(f"Classification fallback to 'conversational': {e}")
        return "conversational"

"""Solution generator for coding, mathematics, and conceptual queries."""
import re
from typing import List, Dict, Any, Optional
from app.services.llm_router import llm_router
from app.utils.prompts import get_solver_prompt
from app.utils.logger import logger


def clean_code_formatting(text: str, query: str) -> str:
    """Post-processes code blocks to respect user constraints (no comments unless asked, no std:: in C++)."""
    wants_comments = any(w in query.lower() for w in ["comment", "explain", "why", "annotate", "breakdown"])
    is_cpp_query = any(w in query.lower() for w in ["c++", "cpp"])

    def process_block(match):
        lang = (match.group(1) or "").strip().lower()
        code = match.group(2)

        # 1. Remove comments if not requested
        if not wants_comments:
            if lang in ("cpp", "c++", "c", "java", "javascript", "js", "ts", "typescript", "cs", "csharp", "go", "rust") or is_cpp_query:
                code = re.sub(r'(?<!:)\s*//(?!/).*$', '', code, flags=re.MULTILINE)
            elif lang in ("python", "py"):
                code = re.sub(r'^\s*#.*$', '', code, flags=re.MULTILINE)
                code = re.sub(r'\s+#.*$', '', code, flags=re.MULTILINE)

        # 2. C++ specific rules: no std:: and ensure using namespace std;
        if lang in ("cpp", "c++") or is_cpp_query:
            # Remove std:: prefix
            code = code.replace("std::", "")
            # Ensure using namespace std; right after headers if headers exist
            if 'using namespace std;' not in code and '#include' in code:
                lines = code.split('\n')
                inc_indices = [i for i, l in enumerate(lines) if l.strip().startswith('#include')]
                if inc_indices:
                    lines.insert(max(inc_indices) + 1, '\nusing namespace std;')
                    code = '\n'.join(lines)

        code = re.sub(r'\n{3,}', '\n\n', code).strip()
        out_lang = match.group(1) or ('cpp' if is_cpp_query else 'python')
        return f"```{out_lang}\n{code}\n```"

    return re.sub(r"```([a-zA-Z0-9_+-]*)\s*\n(.*?)\n\s*```", process_block, text, flags=re.DOTALL)


async def generate_solution(
    query: str,
    task_type: str,
    retrieved_memory: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """Generates direct solution incorporating past learnings."""
    system_prompt = get_solver_prompt(task_type)

    if retrieved_memory and task_type in ("code", "math", "conceptual", "explain"):
        memory_snippets = []
        for item in retrieved_memory:
            # Only inject if similarity distance indicates genuine relevance
            dist = item.get("distance", 1.0)
            if dist < 0.60:
                doc = item.get("document", "")
                if doc:
                    first_lines = "\n".join(doc.strip().split("\n")[:3])
                    if len(first_lines) > 200:
                        first_lines = first_lines[:200] + "..."
                    memory_snippets.append(first_lines)

        if memory_snippets:
            system_prompt += "\n\n### Prior Relevant Context:\n"
            system_prompt += "\n".join(f"- {s}" for s in memory_snippets)

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages.extend(conversation_history[-6:])

    messages.append({"role": "user", "content": query})

    temperature = 0.2 if task_type in ("code", "math") else 0.7

    try:
        solution = await llm_router.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=800
        )
        if task_type == "code" or "```" in solution:
            solution = clean_code_formatting(solution, query)
        return solution
    except Exception as e:
        logger.error(f"Solution generation failed: {e}")
        return f"Error generating solution: {str(e)}"

"""Main autonomous study agent orchestrator."""
from typing import Dict, Any, List, Optional
from app.core.classifier import classify_task
from app.core.solver import generate_solution, clean_code_formatting
from app.core.verifier import verify_and_heal_solution
from app.core.explainer import generate_explanation
from app.memory.vector_store import vector_store
from app.memory.experience_log import log_experience
from app.memory.knowledge_graph import concept_graph
from app.services.groq_client import groq_client
from app.utils.logger import logger


class AutonomousStudyAgent:
    """The master multimodal study agent with self-learning loop."""

    async def run(
        self,
        query: str,
        user_id: str = "default_user",
        mode: str = "answer",
        image_base64: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Executes the autonomous loop:
        1. Retrieve relevant memory
        2. Classify task type
        3. Formulate verified solution (with sandbox testing if code)
        4. Synthesize personalized explanation
        5. Update memory & knowledge structures
        """
        logger.info(f"Processing query: '{query[:80]}...' [Mode: {mode}]")

        memories = []
        if image_base64:
            clean_b64 = image_base64
            mime_type = "image/jpeg"
            if clean_b64.startswith("data:") and ";base64," in clean_b64:
                header, clean_b64 = clean_b64.split(";base64,", 1)
                mime_type = header.replace("data:", "").strip()
            
            task_type = "diagram"
            prompt_q = query if query and query.strip() else "Please analyze this image or diagram thoroughly and explain what it depicts."
            solution = await groq_client.chat_with_vision(
                prompt_text=prompt_q,
                image_base64=clean_b64,
                mime_type=mime_type
            )
            verified_solution = solution
            verification_result = {"passed": True}
        else:
            # 1. Retrieve relevant memories (Prior experience)
            memories = await vector_store.search_similar(query=query, user_id=user_id, top_k=3)
            if memories:
                logger.info(f"Retrieved {len(memories)} past relevant memory items.")

            # 2. Classify intent
            task_type = await classify_task(query)
            logger.info(f"Classified task type: '{task_type}'")

            # 3. Generate initial solution
            solution = await generate_solution(
                query=query,
                task_type=task_type,
                retrieved_memory=memories,
                conversation_history=conversation_history
            )

            # 4. Verify & Self-Heal in Sandbox (only if code solution and code block present)
            if task_type == "code" and "```" in solution:
                verified_solution, verification_result = await verify_and_heal_solution(solution, query)
            else:
                verified_solution, verification_result = solution, {"passed": True}

        # 5. Generate specialized pedagogical explanation only if explicitly requested
        explanation = ""
        if mode in ("socratic", "simple", "analogy") and not image_base64:
            explanation = await generate_explanation(
                query=query,
                solution=verified_solution,
                mode=mode
            )

        final_reply = explanation if explanation else verified_solution
        if "```" in final_reply:
            final_reply = clean_code_formatting(final_reply, query)

        # 6. Self-Learning: Record this experience into memory
        is_success = verification_result.get("passed") is not False
        await log_experience(
            query=query,
            solution=final_reply,
            task_type=task_type,
            explanation=explanation,
            success=is_success,
            user_id=user_id,
            metadata={"mode": mode, "code_verified": verification_result.get("passed")}
        )

        # 7. Check & enrich concept graph
        try:
            concept_graph.add_concept_relation(
                prereq=task_type.capitalize(),
                concept=query[:40].strip(),
                category="StudyTopic"
            )
        except Exception:
            pass

        return {
            "reply": final_reply,
            "solution": verified_solution,
            "explanation": explanation,
            "task_type": task_type,
            "code_output": verification_result.get("output"),
            "code_passed": verification_result.get("passed"),
            "retrieved_memory": memories
        }


study_agent = AutonomousStudyAgent()

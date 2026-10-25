"""Smart LLM Router: Routes to Groq -> Ollama -> or Dev Mock fallback."""
from typing import List, Dict, Any, Optional
from app.services.groq_client import groq_client
from app.services.ollama_client import ollama_client
from app.utils.logger import logger


class LLMRouter:
    """Intelligently routes model queries to Groq or local Ollama."""

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        require_vision: bool = False,
        image_base64: Optional[str] = None,
        mime_type: str = "image/jpeg",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model: Optional[str] = None
    ) -> str:
        # 1. Vision path
        if require_vision and image_base64:
            if groq_client.is_configured():
                try:
                    last_text = messages[-1]["content"] if messages and isinstance(messages[-1]["content"], str) else "Describe this image."
                    return await groq_client.chat_with_vision(last_text, image_base64, mime_type=mime_type, model=model)
                except Exception as e:
                    logger.error(f"Groq vision failed: {e}")
            return "Vision analysis requires a configured GROQ_API_KEY in .env."

        # 2. Regular Chat with Groq
        if groq_client.is_configured():
            try:
                return await groq_client.chat(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except Exception as e:
                logger.warning(f"Groq API call encountered error: {e}. Attempting alternative model...")
                # If specific model hit rate limit, try lightweight fallback model on user's key
                fallback_models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
                for fb_model in fallback_models:
                    if fb_model != model:
                        try:
                            logger.info(f"Retrying with fallback model '{fb_model}'...")
                            return await groq_client.chat(
                                messages=messages,
                                model=fb_model,
                                temperature=temperature,
                                max_tokens=min(max_tokens or 600, 600)
                            )
                        except Exception as fb_err:
                            logger.warning(f"Fallback model '{fb_model}' also failed: {fb_err}")

                # If all Groq attempts failed, check Ollama
                if await ollama_client.is_available():
                    try:
                        logger.info("Serving query via local Ollama...")
                        return await ollama_client.chat(
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                    except Exception:
                        pass

                return f"**KitAi:** Groq API rate limit or service delay: {str(e)[:120]}. Please try again in a few moments."

        # 3. Fallback to Local Ollama if no Groq key configured
        if await ollama_client.is_available():
            try:
                logger.info("Serving query via local Ollama...")
                return await ollama_client.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except Exception as e:
                logger.error(f"Ollama inference error: {e}")

        # 4. Only if no API key is configured at all
        last_msg = messages[-1]["content"] if messages else ""
        return (
            f"**KitAi:** Welcome! To get instant AI responses and code generation, "
            f"please click the **Settings** icon and enter your Groq API key (or configure `GROQ_API_KEY` in `.env`)."
        )


llm_router = LLMRouter()

import logging
from typing import Optional

logger = logging.getLogger("llm_factory")


class _CleanChatGoogleGenerativeAI:
    """
    Thin wrapper around ChatGoogleGenerativeAI that collapses list-format
    content blocks (produced by thinking-enabled Gemma models) into a single
    plain string before returning the response.
    """
    def __new__(cls, *args, **kwargs):
        from langchain_google_genai import ChatGoogleGenerativeAI

        class _Inner(ChatGoogleGenerativeAI):
            def invoke(self, *a, **kw):
                response = super().invoke(*a, **kw)
                if hasattr(response, "content") and isinstance(response.content, list):
                    text_parts = [
                        (part.get("text", "") if isinstance(part, dict) else part)
                        for part in response.content
                        if not isinstance(part, dict) or part.get("type") == "text"
                    ]
                    response.content = "".join(text_parts)
                return response

        return _Inner(*args, **kwargs)


def get_chat_llm(
    model_name: str = "gemma-4-31b-it",
    temperature: float = 0.0,
    api_key: Optional[str] = None,
):
    """
    Return a ChatGoogleGenerativeAI instance.

    Parameters
    ----------
    model_name : str
        Gemini/Gemma model identifier (default: gemma-4-31b-it).
    temperature : float
        Sampling temperature (0.0 = deterministic).
    api_key : str, optional
        Google Gemini API key.  When provided, it overrides any key found in
        environment variables, enabling per-request API key injection from
        the Streamlit UI without touching .env files.
    """
    import os
    resolved_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not resolved_key:
        logger.warning("No Gemini API key found. Calls to the LLM will fail.")

    logger.info(
        "Initializing ChatGoogleGenerativeAI: model=%s, temp=%.1f, key_source=%s",
        model_name, temperature, "runtime" if api_key else "env",
    )
    return _CleanChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=resolved_key,
    )

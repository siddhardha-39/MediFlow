# extractor.py
"""
Raw LLM extraction layer.

Responsibilities:
- Initialise the local Ollama model
- Send the extraction prompt
- Return the raw string response

NOTE: This module intentionally does NOT parse or validate.
      That is handled downstream by parser.py → validator.py → retry_handler.py.
"""
from langchain_core.messages import HumanMessage

from config import MEDIFLOW_LLM_MODEL
from llm_factory import get_chat_llm
from structured_outputs.prompts import EXTRACTION_PROMPT, RETRY_PROMPT
from structured_outputs.utils import get_logger, truncate

logger = get_logger("extractor")

# ── Model configuration ────────────────────────────────────────────────────────
MODEL_NAME  = MEDIFLOW_LLM_MODEL
TEMPERATURE = 0.0        # deterministic — essential for structured extraction

llm = get_chat_llm(model_name=MODEL_NAME, temperature=TEMPERATURE)


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_raw(patient_text: str) -> str:
    """
    Send the extraction prompt to the LLM and return the raw text response.

    Args:
        patient_text: Free-text patient history or summary.

    Returns:
        Raw LLM output string (may or may not be valid JSON).
    """
    prompt = EXTRACTION_PROMPT.format(patient_text=patient_text)
    logger.info("Sending extraction prompt for patient text: %s", truncate(patient_text))

    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()

    logger.debug("Raw LLM output: %s", truncate(raw))
    return raw


def extract_retry(patient_text: str, previous_response: str, error: str) -> str:
    """
    Send a corrective retry prompt when the initial response was invalid.

    Args:
        patient_text:      Original patient text.
        previous_response: The bad LLM output from the previous attempt.
        error:             The error message from the parser or validator.

    Returns:
        Raw LLM output string from the retry attempt.
    """
    prompt = RETRY_PROMPT.format(
        patient_text=patient_text,
        previous_response=previous_response,
        error=error,
    )
    logger.warning("Retrying extraction. Previous error: %s", error)

    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()

    logger.debug("Retry raw output: %s", truncate(raw))
    return raw

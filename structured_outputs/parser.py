# parser.py
"""
JSON parsing layer.

Responsibilities:
- Accept raw LLM output (which may contain markdown fences, prose, etc.)
- Extract the first valid JSON object
- Return a clean Python dict or raise a descriptive error
"""
import json
import re
from typing import Any, Dict

from structured_outputs.utils import get_logger, truncate

logger = get_logger("parser")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` code fences from LLM output."""
    # Match fenced code blocks (optional language tag)
    fenced = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", text, flags=re.IGNORECASE)
    return fenced.strip()


def _extract_json_object(text: str) -> str:
    """
    Find the first '{...}' JSON object inside a string.
    Handles cases where the LLM adds prose before/after the JSON.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in LLM output.")

    # Walk forward tracking brace depth to find matching closing brace
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth == 0:
            return text[start : i + 1]

    raise ValueError("JSON object in LLM output is not properly closed.")


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_llm_output(raw: str) -> Dict[str, Any]:
    """
    Parse raw LLM output into a Python dictionary.

    Steps:
        1. Strip markdown fences.
        2. Extract the first complete JSON object.
        3. Parse with json.loads().

    Args:
        raw: Raw string output from the LLM.

    Returns:
        Parsed dictionary.

    Raises:
        ValueError: If no valid JSON can be extracted.
        json.JSONDecodeError: If the extracted string isn't valid JSON.
    """
    logger.debug("Parsing raw output: %s", truncate(raw))

    cleaned = _strip_markdown_fences(raw)
    json_str = _extract_json_object(cleaned)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise

    logger.info("Parsed JSON successfully — keys: %s", list(data.keys()))
    return data

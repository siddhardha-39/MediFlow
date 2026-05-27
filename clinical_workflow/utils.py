# clinical_workflow/utils.py
"""
Shared utilities for the clinical workflow nodes.

Extracted here to avoid code duplication across soap_formatter.py
and corrector.py, which both need to parse JSON from LLM responses.
"""
import json
import re
import logging

logger = logging.getLogger("workflow.utils")


def parse_llm_json(raw: str) -> dict:
    """
    Extract a JSON object from raw LLM output.

    Handles common LLM quirks:
    - Markdown code fences (```json ... ```)
    - Leading/trailing text outside the JSON
    - Nested braces

    Args:
        raw: Raw LLM response text.

    Returns:
        Parsed dict, or empty dict if parsing fails.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", raw).strip()

    # Find the first opening brace
    start = cleaned.find("{")
    if start == -1:
        logger.warning("parse_llm_json: No JSON object found in response")
        return {}

    # Walk forward tracking brace depth to find the matching close
    depth = 0
    for i, ch in enumerate(cleaned[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth == 0:
            try:
                return json.loads(cleaned[start:i + 1])
            except json.JSONDecodeError as e:
                logger.warning("parse_llm_json: Invalid JSON - %s", e)
                return {}

    logger.warning("parse_llm_json: Unbalanced braces in response")
    return {}

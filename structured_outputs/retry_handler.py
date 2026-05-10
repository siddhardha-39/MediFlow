# retry_handler.py
"""
Retry handling layer.

Responsibilities:
- Orchestrate extraction → parsing → validation in a retry loop
- On failure, send a corrective prompt back to the LLM
- Return a fallback PatientInfo if all attempts are exhausted
"""
import json
from pydantic import ValidationError

from structured_outputs.models import PatientInfo, ExtractionResult
from structured_outputs.extractor import extract_raw, extract_retry
from structured_outputs.parser import parse_llm_output
from structured_outputs.validator import validate
from structured_outputs.utils import get_logger

logger = get_logger("retry_handler")

MAX_RETRIES = 3


# ── Fallback ───────────────────────────────────────────────────────────────────

def _fallback_result(patient_text: str, raw: str, error: str, retries: int) -> ExtractionResult:
    """Return an empty-but-valid PatientInfo when all retries are exhausted."""
    logger.error("All %d retries exhausted. Returning fallback result.", retries)
    return ExtractionResult(
        success=False,
        patient_info=PatientInfo(),           # all fields default to []
        raw_output=raw,
        error=error,
        retries_used=retries,
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def run_with_retry(patient_text: str) -> ExtractionResult:
    """
    Run the full extract → parse → validate pipeline with automatic retry.

    Retry strategy:
        - Attempt 0:    standard extraction prompt
        - Attempts 1-N: corrective retry prompt that includes the previous
                        bad response and the error message
        - After MAX_RETRIES: return a fallback ExtractionResult

    Args:
        patient_text: Free-text patient history.

    Returns:
        ExtractionResult with success flag, validated data, and metadata.
    """
    raw = ""
    error = ""

    for attempt in range(MAX_RETRIES + 1):
        try:
            # ── Step 1: Extract ──────────────────────────────────────────
            if attempt == 0:
                raw = extract_raw(patient_text)
            else:
                raw = extract_retry(patient_text, previous_response=raw, error=error)

            # ── Step 2: Parse ────────────────────────────────────────────
            data = parse_llm_output(raw)

            # ── Step 3: Validate ─────────────────────────────────────────
            patient = validate(data)

            logger.info("Pipeline succeeded on attempt %d.", attempt)
            return ExtractionResult(
                success=True,
                patient_info=patient,
                raw_output=raw,
                retries_used=attempt,
            )

        except (ValueError, json.JSONDecodeError) as e:
            error = f"JSON parsing error: {e}"
            logger.warning("Attempt %d failed (parse): %s", attempt, error)

        except ValidationError as e:
            error = f"Validation error: {e}"
            logger.warning("Attempt %d failed (validation): %s", attempt, error)

        except Exception as e:
            error = f"Unexpected error: {e}"
            logger.error("Attempt %d failed (unexpected): %s", attempt, error)

    return _fallback_result(patient_text, raw, error, MAX_RETRIES)

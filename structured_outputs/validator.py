# validator.py
"""
Pydantic validation layer.

Responsibilities:
- Accept a parsed Python dict
- Validate and coerce it into a PatientInfo object
- Raise descriptive errors for schema violations
"""
from typing import Any, Dict

from pydantic import ValidationError

from structured_outputs.models import PatientInfo
from structured_outputs.utils import get_logger

logger = get_logger("validator")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _coerce_list_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Defensive coercion: if any expected list field is a string,
    wrap it in a list so Pydantic doesn't reject it outright.
    """
    list_fields = ["conditions", "allergies", "medications", "symptoms"]
    for field in list_fields:
        if field in data and isinstance(data[field], str):
            logger.warning("Field '%s' is a string — wrapping in list.", field)
            data[field] = [data[field]] if data[field].strip() else []
        # Fill missing fields with empty lists (Pydantic already does this via default_factory)
    return data


# ── Public API ─────────────────────────────────────────────────────────────────

def validate(data: Dict[str, Any]) -> PatientInfo:
    """
    Validate a parsed dictionary against the PatientInfo Pydantic schema.

    Args:
        data: Dictionary produced by parser.parse_llm_output().

    Returns:
        A validated PatientInfo instance.

    Raises:
        ValidationError: If the data violates the schema and cannot be coerced.
    """
    data = _coerce_list_fields(data)

    try:
        patient = PatientInfo(**data)
        logger.info(
            "Validation passed — conditions=%d  allergies=%d  "
            "medications=%d  symptoms=%d",
            len(patient.conditions),
            len(patient.allergies),
            len(patient.medications),
            len(patient.symptoms),
        )
        return patient
    except ValidationError as e:
        logger.error("Validation failed: %s", e)
        raise

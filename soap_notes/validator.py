# soap_notes/validator.py
"""
SOAP note validation layer.

Checks that all 4 SOAP sections are populated and flags quality issues.
This ensures doctors see warnings about incomplete documentation.
"""
import logging
from soap_notes.models import SOAPNote, SOAPValidation

logger = logging.getLogger("soap_notes.validator")

# Minimum character count for a section to be considered "present"
MIN_SECTION_LENGTH = 10


def validate_soap(note: SOAPNote) -> SOAPValidation:
    """
    Validate a SOAP note for completeness and quality.

    Checks:
    1. Are all 4 sections non-empty?
    2. Are sections long enough to be meaningful?
    3. Any obvious quality issues?
    """
    missing = []
    warnings = []

    sections = {
        "Subjective": note.subjective,
        "Objective": note.objective,
        "Assessment": note.assessment,
        "Plan": note.plan,
    }

    for name, content in sections.items():
        if not content or not content.strip():
            missing.append(name)
        elif len(content.strip()) < MIN_SECTION_LENGTH:
            warnings.append(f"{name} section is very short ({len(content.strip())} chars)")
        elif content.strip().lower() in ("not documented in this visit", "n/a", "none"):
            warnings.append(f"{name} section has no clinical content")

    is_complete = len(missing) == 0

    if is_complete and not warnings:
        logger.info("SOAP validation passed - all sections complete")
    else:
        logger.warning(
            "SOAP validation: missing=%s, warnings=%d",
            missing, len(warnings),
        )

    return SOAPValidation(
        is_complete=is_complete,
        missing_sections=missing,
        warnings=warnings,
    )

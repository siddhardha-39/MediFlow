# soap_notes/service.py
"""
SOAP note service — orchestrates the full pipeline.

Pipeline:
    transcript_text
        -> generate SOAP note (LLM)
        -> parse JSON
        -> validate completeness
        -> extract medical entities (Stage 2)
        -> return SOAPResult
"""
import logging
from soap_notes.generator import generate_soap_raw, parse_soap
from soap_notes.validator import validate_soap
from soap_notes.models import SOAPResult

# Import Stage 2 extraction pipeline
from structured_outputs.retry_handler import run_with_retry

logger = logging.getLogger("soap_notes.service")


def generate_soap_note(transcript_text: str) -> SOAPResult:
    """
    Full SOAP note generation pipeline.

    Steps:
        1. Generate SOAP note from transcript via LLM
        2. Parse the raw output into a SOAPNote object
        3. Validate completeness (flag missing sections)
        4. Extract medical entities using Stage 2 pipeline
        5. Return complete SOAPResult
    """
    logger.info("=== SOAP Note Pipeline Start ===")

    # Step 1-2: Generate and parse
    raw = generate_soap_raw(transcript_text)
    soap_note = parse_soap(raw)
    logger.info("SOAP note generated: S=%d O=%d A=%d P=%d chars",
                len(soap_note.subjective), len(soap_note.objective),
                len(soap_note.assessment), len(soap_note.plan))

    # Step 3: Validate
    validation = validate_soap(soap_note)

    # Step 4: Extract medical entities using Stage 2 pipeline
    patient_info = None
    try:
        extraction = run_with_retry(transcript_text)
        if extraction.success and extraction.patient_info:
            patient_info = extraction.patient_info.model_dump()
            logger.info("Medical entities extracted: %s", patient_info)
    except Exception as e:
        logger.warning("Medical entity extraction failed: %s", e)

    # Step 5: Combine into result
    result = SOAPResult(
        soap_note=soap_note,
        validation=validation,
        patient_info=patient_info,
        transcript_text=transcript_text,
    )

    logger.info("=== SOAP Note Pipeline Complete ===")
    return result

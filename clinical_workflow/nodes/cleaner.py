# clinical_workflow/nodes/cleaner.py
"""
Node: Clean the raw transcript.

WHY A SEPARATE CLEANER NODE:
    Whisper output contains filler words ("um", "uh", "like", "you know"),
    repeated words, and formatting issues. Cleaning BEFORE sending to the
    LLM for SOAP generation improves output quality.

    By making this a separate node (instead of embedding it in the formatter),
    we can:
    - Test cleaning independently
    - Skip it if the input is already clean (e.g., typed text)
    - Swap in a more advanced cleaner later (NLP-based, LLM-based)

LANGGRAPH CONCEPT — NODE INDEPENDENCE:
    Each node should do ONE thing and do it well.
    Nodes don't know about each other — they only know about the state.
"""
import re
import logging
from clinical_workflow.state import ClinicalWorkflowState

logger = logging.getLogger("workflow.node.cleaner")

# Common filler words in spoken English
FILLER_WORDS = [
    r"\bum\b", r"\buh\b", r"\bumm\b", r"\buhh\b",
    r"\blike\b,?\s*\blike\b",     # repeated "like"
    r"\byou know\b",
    r"\bI mean\b",
    r"\bso basically\b",
    r"\bactually\b,?\s*\bactually\b",
]


def cleaner_node(state: ClinicalWorkflowState) -> dict:
    """
    Clean raw transcript by removing filler words and fixing formatting.

    Reads:  state["raw_transcript"]
    Writes: state["clean_transcript"]
    """
    raw = state.get("raw_transcript", "")
    logger.info("CLEANER: Input length = %d chars", len(raw))

    if not raw.strip():
        logger.warning("CLEANER: Empty transcript, passing through")
        return {"clean_transcript": raw}

    cleaned = raw

    # Remove filler words (case-insensitive)
    for pattern in FILLER_WORDS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Fix multiple spaces
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    # Fix space before punctuation
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)

    # Capitalize after periods
    cleaned = re.sub(
        r"([.!?])\s+([a-z])",
        lambda m: m.group(1) + " " + m.group(2).upper(),
        cleaned,
    )

    cleaned = cleaned.strip()
    logger.info("CLEANER: Output length = %d chars (removed %d chars)",
                len(cleaned), len(raw) - len(cleaned))

    return {"clean_transcript": cleaned}

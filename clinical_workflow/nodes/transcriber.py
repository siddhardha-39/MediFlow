# clinical_workflow/nodes/transcriber.py
"""
Node: Transcribe doctor audio to text.

LANGGRAPH CONCEPT — NODE:
    A node is a regular Python function that:
    1. Receives the current state (as a dict)
    2. Does some work
    3. Returns a dict of state UPDATES (not the full state)

    LangGraph MERGES your updates into the existing state.
    You only return the fields you changed.

WHAT THIS NODE DOES:
    Takes audio_path from state -> runs faster-whisper -> sets raw_transcript.
    This reuses our Stage 3 transcription module.
"""
import logging
from clinical_workflow.state import ClinicalWorkflowState

logger = logging.getLogger("workflow.node.transcriber")


def transcriber_node(state: ClinicalWorkflowState) -> dict:
    """
    Transcribe audio file to text using faster-whisper.

    Reads:  state["audio_path"]
    Writes: state["raw_transcript"]
    """
    audio_path = state.get("audio_path", "")
    logger.info("TRANSCRIBER: Processing %s", audio_path)

    # If transcript is already provided (text mode / demo mode), skip transcription
    existing = state.get("raw_transcript", "")
    if existing and not audio_path:
        logger.info("TRANSCRIBER: Transcript already provided (%d chars), skipping", len(existing))
        return {"raw_transcript": existing}

    if not audio_path:
        logger.warning("TRANSCRIBER: No audio path and no transcript, returning empty")
        return {"raw_transcript": ""}

    try:
        # Reuse Stage 3 transcription module
        from transcription.preprocessor import preprocess_audio
        from transcription.transcriber import transcribe

        import os
        processed_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "processed")
        processed_path = preprocess_audio(audio_path, processed_dir)
        result = transcribe(processed_path)

        logger.info("TRANSCRIBER: Got %d chars, %d segments", len(result.full_text), len(result.segments))
        return {"raw_transcript": result.full_text}

    except Exception as e:
        logger.error("TRANSCRIBER: Failed - %s", e)
        return {"raw_transcript": f"[Transcription failed: {e}]"}

# clinical_workflow/nodes/transcriber.py
"""
Node: Pass raw transcript text into the workflow state.

LANGGRAPH CONCEPT — NODE:
    A node is a regular Python function that:
    1. Receives the current state (as a dict)
    2. Does some work
    3. Returns a dict of state UPDATES (not the full state)

    LangGraph MERGES your updates into the existing state.
    You only return the fields you changed.

WHAT THIS NODE DOES:
    Accepts raw_transcript text directly from the caller — no audio
    file handling or Whisper model loading required.
"""
import logging
from clinical_workflow.state import ClinicalWorkflowState

logger = logging.getLogger("workflow.node.transcriber")


def transcriber_node(state: ClinicalWorkflowState) -> dict:
    """
    Pass the raw transcript text through to the next workflow stage.

    Reads:  state["raw_transcript"]
    Writes: state["raw_transcript"] (unchanged pass-through)
    """
    transcript = (state.get("raw_transcript") or "").strip()
    logger.info("TRANSCRIBER: Received transcript (%d chars)", len(transcript))
    return {"raw_transcript": transcript}

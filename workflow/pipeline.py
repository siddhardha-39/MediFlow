# workflow/pipeline.py
"""
Simple workflow orchestration using LangGraph.

WHAT IS LANGGRAPH:
    LangGraph lets you define a workflow as a GRAPH of steps.
    Each step (node) is a Python function.
    Edges define the order: which step runs after which.
    Conditional edges let you branch: "if validation fails, retry."

WHY LANGGRAPH INSTEAD OF PLAIN PYTHON:
    You COULD chain functions with plain Python (and we did in service.py).
    LangGraph adds:
    1. Visual graph — you can see the flow
    2. Conditional branching — easy retry/fallback logic
    3. State management — each step reads/writes shared state
    4. Built-in checkpointing — can resume interrupted workflows

    For our use case, the main benefit is conditional retry:
    if SOAP note validation fails, retry generation before giving up.

GRAPH STRUCTURE:
    [transcribe] -> [generate_soap] -> [validate] --(pass)--> [save] -> [done]
                                           |
                                           +--(fail)--> [retry] -> [validate]
                                                           |
                                                           +--(max retries)--> [save_incomplete] -> [done]

IMPORTANT:
    This is a SIMPLE workflow graph. Not an autonomous agent.
    Each node does ONE thing. The graph handles the flow.
"""
import logging
import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from soap_notes.generator import generate_soap_raw, parse_soap
from soap_notes.validator import validate_soap
from structured_outputs.retry_handler import run_with_retry
from database.db import create_patient, get_patient_by_name, create_session

logger = logging.getLogger("workflow.pipeline")

MAX_RETRIES = 2


# ── State Definition ──────────────────────────────────────────────────────────
# TypedDict defines the shape of data flowing through the graph.
# Every node reads from and writes to this shared state.

class PipelineState(TypedDict):
    # Inputs
    transcript: str
    patient_name: str
    audio_file: Optional[str]

    # Intermediate
    soap_raw: Optional[str]
    soap_subjective: Optional[str]
    soap_objective: Optional[str]
    soap_assessment: Optional[str]
    soap_plan: Optional[str]
    is_valid: Optional[bool]
    missing_sections: Optional[list]
    warnings: Optional[list]
    retry_count: int

    # Extracted entities
    conditions: Optional[list]
    medications: Optional[list]
    allergies: Optional[list]
    symptoms: Optional[list]

    # Outputs
    patient_id: Optional[int]
    session_id: Optional[int]
    final_status: Optional[str]


# ── Node Functions ─────────────────────────────────────────────────────────────
# Each function is a graph node. It receives the state, does work, returns updates.

def generate_soap_node(state: PipelineState) -> dict:
    """Node: Generate SOAP note from transcript."""
    logger.info("Node: generate_soap")
    raw = generate_soap_raw(state["transcript"])
    note = parse_soap(raw)

    return {
        "soap_raw": raw,
        "soap_subjective": note.subjective,
        "soap_objective": note.objective,
        "soap_assessment": note.assessment,
        "soap_plan": note.plan,
    }


def validate_node(state: PipelineState) -> dict:
    """Node: Validate the SOAP note for completeness."""
    logger.info("Node: validate")
    from soap_notes.models import SOAPNote
    note = SOAPNote(
        subjective=state.get("soap_subjective", ""),
        objective=state.get("soap_objective", ""),
        assessment=state.get("soap_assessment", ""),
        plan=state.get("soap_plan", ""),
    )
    validation = validate_soap(note)

    return {
        "is_valid": validation.is_complete,
        "missing_sections": validation.missing_sections,
        "warnings": validation.warnings,
    }


def extract_entities_node(state: PipelineState) -> dict:
    """Node: Extract medical entities using Stage 2 pipeline."""
    logger.info("Node: extract_entities")
    try:
        result = run_with_retry(state["transcript"])
        if result.success and result.patient_info:
            info = result.patient_info
            return {
                "conditions": info.conditions,
                "medications": info.medications,
                "allergies": info.allergies,
                "symptoms": info.symptoms,
            }
    except Exception as e:
        logger.warning("Entity extraction failed: %s", e)

    return {"conditions": [], "medications": [], "allergies": [], "symptoms": []}


def save_node(state: PipelineState) -> dict:
    """Node: Save patient record to database."""
    logger.info("Node: save")
    name = state.get("patient_name", "Unknown Patient")

    # Find or create patient
    patient = get_patient_by_name(name)
    if patient:
        patient_id = patient["id"]
    else:
        patient_id = create_patient(name)

    # Create session
    soap = {
        "subjective": state.get("soap_subjective", ""),
        "objective": state.get("soap_objective", ""),
        "assessment": state.get("soap_assessment", ""),
        "plan": state.get("soap_plan", ""),
    }
    patient_info = {
        "conditions": state.get("conditions", []),
        "medications": state.get("medications", []),
        "allergies": state.get("allergies", []),
        "symptoms": state.get("symptoms", []),
    }

    session_id = create_session(
        patient_id,
        audio_file=state.get("audio_file"),
        transcript=state["transcript"],
        soap_note=soap,
        patient_info=patient_info,
    )

    is_valid = state.get("is_valid", False)
    status = "complete" if is_valid else "incomplete - saved with warnings"

    return {
        "patient_id": patient_id,
        "session_id": session_id,
        "final_status": status,
    }


def retry_node(state: PipelineState) -> dict:
    """Node: Increment retry counter (actual regeneration happens in generate_soap)."""
    logger.info("Node: retry (attempt %d)", state.get("retry_count", 0) + 1)
    return {"retry_count": state.get("retry_count", 0) + 1}


# ── Conditional Edge ───────────────────────────────────────────────────────────

def should_retry(state: PipelineState) -> str:
    """
    Decide whether to retry SOAP generation or proceed to save.

    This is the CONDITIONAL BRANCHING that makes LangGraph useful.
    """
    if state.get("is_valid", False):
        return "extract"   # Valid -> extract entities -> save
    elif state.get("retry_count", 0) < MAX_RETRIES:
        return "retry"     # Invalid + retries left -> try again
    else:
        return "extract"   # Invalid + no retries left -> save anyway with warnings


# ── Build the Graph ────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    """
    Build the clinical documentation workflow graph.

    Graph:
        generate_soap -> validate -> (conditional) -> extract -> save -> END
                                         |
                                         +-> retry -> generate_soap (loop)
    """
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("generate_soap", generate_soap_node)
    graph.add_node("validate", validate_node)
    graph.add_node("extract", extract_entities_node)
    graph.add_node("save", save_node)
    graph.add_node("retry", retry_node)

    # Add edges
    graph.set_entry_point("generate_soap")
    graph.add_edge("generate_soap", "validate")

    # Conditional: after validation, retry or proceed
    graph.add_conditional_edges("validate", should_retry, {
        "extract": "extract",
        "retry": "retry",
    })

    graph.add_edge("retry", "generate_soap")  # retry loops back
    graph.add_edge("extract", "save")
    graph.add_edge("save", END)

    return graph


# ── Public API ─────────────────────────────────────────────────────────────────

# Compile the graph once at module level
pipeline = build_pipeline().compile()


def run_pipeline(transcript: str, patient_name: str,
                 audio_file: str = None) -> dict:
    """
    Run the full clinical documentation pipeline.

    Args:
        transcript:   The transcribed text from a doctor-patient conversation.
        patient_name: The patient's name.
        audio_file:   Optional original audio filename.

    Returns:
        Final pipeline state dict with all results.
    """
    logger.info("=== Pipeline Start: %s ===", patient_name)

    initial_state = {
        "transcript": transcript,
        "patient_name": patient_name,
        "audio_file": audio_file,
        "retry_count": 0,
    }

    result = pipeline.invoke(initial_state)

    logger.info(
        "=== Pipeline Complete: status=%s, patient_id=%s, session_id=%s ===",
        result.get("final_status"),
        result.get("patient_id"),
        result.get("session_id"),
    )

    return result

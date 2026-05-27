# clinical_workflow/nodes/saver.py
"""
Node: Save the approved clinical record to SQLite.

This is the FINAL node in the happy path:
    transcribe -> clean -> format -> validate -> approve -> SAVE -> END

Reuses the database module from Stage 3.
"""
import logging
from clinical_workflow.state import ClinicalWorkflowState
from database.db import create_patient, get_patient_by_name, create_session, init_db

logger = logging.getLogger("workflow.node.saver")


def saver_node(state: ClinicalWorkflowState) -> dict:
    """
    Save patient record to SQLite database.

    Reads:  all state fields
    Writes: state["patient_id"], state["session_id"], state["final_status"]
    """
    # Ensure DB is initialized
    init_db()

    patient_name = state.get("patient_name", "Unknown Patient")
    logger.info("SAVER: Saving record for %s", patient_name)

    # Find or create patient
    patient = get_patient_by_name(patient_name)
    if patient:
        patient_id = patient["id"]
        logger.info("SAVER: Found existing patient ID=%d", patient_id)
    else:
        patient_id = create_patient(patient_name)
        logger.info("SAVER: Created new patient ID=%d", patient_id)

    # Build SOAP dict
    soap_note = {
        "subjective": state.get("soap_subjective", ""),
        "objective": state.get("soap_objective", ""),
        "assessment": state.get("soap_assessment", ""),
        "plan": state.get("soap_plan", ""),
    }

    # Build entities dict
    patient_info = {
        "conditions": state.get("conditions", []),
        "medications": state.get("medications", []),
        "allergies": state.get("allergies", []),
        "symptoms": state.get("symptoms", []),
    }

    # Save session
    session_id = create_session(
        patient_id,
        audio_file=state.get("audio_path"),
        transcript=state.get("clean_transcript") or state.get("raw_transcript"),
        soap_note=soap_note,
        patient_info=patient_info,
    )

    status = "saved" if state.get("doctor_approved") or state.get("is_valid", False) else "incomplete"
    logger.info("SAVER: Record saved - patient_id=%d, session_id=%d, status=%s",
                patient_id, session_id, status)

    print(f"\n  [SAVED] Patient ID: {patient_id}, Session ID: {session_id}")

    return {
        "patient_id": patient_id,
        "session_id": session_id,
        "final_status": status,
    }

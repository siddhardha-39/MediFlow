# tools/clinical_tools.py
"""
LangChain tools for the clinical documentation agent.

WHAT IS A LANGCHAIN TOOL:
    A Tool is a Python function that an LLM agent can call.
    The agent reads the tool's name and description, decides
    WHEN to call it, and passes the right arguments.

    Think of tools as "abilities" you give to the AI:
    - "transcribe_audio" = the agent can transcribe audio files
    - "generate_soap_note" = the agent can create SOAP notes
    - "save_patient_record" = the agent can save to the database

TOOL CALLING FLOW:
    1. User gives the agent a task
    2. Agent reads available tools
    3. Agent decides which tool to use
    4. Agent calls the tool with arguments
    5. Tool returns a result
    6. Agent uses the result to answer

WHY SEPARATE TOOLS FROM MODULES:
    The tools are THIN WRAPPERS around the actual module functions.
    They exist only to give the LLM agent a clean interface.
    The real logic lives in transcription/, soap_notes/, database/.
"""
import logging
from langchain_core.tools import tool

from transcription.service import process_audio
from soap_notes.service import generate_soap_note
from soap_notes.models import SOAPResult
from database.db import (
    create_patient, get_patient, get_patient_by_name,
    create_session, get_patient_sessions, get_patient_history,
)

logger = logging.getLogger("tools.clinical_tools")


# ── Tool 1: Transcribe Audio ──────────────────────────────────────────────────

@tool
def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe a doctor's audio recording to text.
    Use this when you have an audio file that needs to be converted to text.

    Args:
        audio_path: Full path to the audio file (.wav, .mp3, etc.)

    Returns:
        The full transcript text.
    """
    import os
    filename = os.path.basename(audio_path)
    result = process_audio(audio_path, filename)
    return result.full_text


# ── Tool 2: Generate SOAP Note ────────────────────────────────────────────────

@tool
def generate_soap(transcript_text: str) -> str:
    """
    Generate a structured SOAP note from a doctor-patient transcript.
    Use this after transcription to create clinical documentation.

    Args:
        transcript_text: The full transcript text from a doctor-patient conversation.

    Returns:
        A formatted SOAP note with Subjective, Objective, Assessment, and Plan sections.
    """
    result = generate_soap_note(transcript_text)
    note = result.soap_note

    output = f"""SOAP Note:

S (Subjective): {note.subjective}

O (Objective): {note.objective}

A (Assessment): {note.assessment}

P (Plan): {note.plan}

Validation: {"Complete" if result.validation.is_complete else "Incomplete - Missing: " + ", ".join(result.validation.missing_sections)}"""

    if result.patient_info:
        output += f"\n\nMedical Entities: {result.patient_info}"

    return output


# ── Tool 3: Validate SOAP Note ────────────────────────────────────────────────

@tool
def validate_note(transcript_text: str) -> str:
    """
    Validate a clinical note for completeness.
    Use this to check if all required sections are present.

    Args:
        transcript_text: The transcript to validate.

    Returns:
        Validation result showing missing sections and warnings.
    """
    result = generate_soap_note(transcript_text)
    v = result.validation

    if v.is_complete and not v.warnings:
        return "Note is complete. All SOAP sections are present."

    lines = []
    if v.missing_sections:
        lines.append(f"Missing sections: {', '.join(v.missing_sections)}")
    if v.warnings:
        for w in v.warnings:
            lines.append(f"Warning: {w}")

    return "\n".join(lines) if lines else "Note is complete."


# ── Tool 4: Save Patient Record ───────────────────────────────────────────────

@tool
def save_patient_record(patient_name: str, transcript: str,
                        soap_subjective: str = "", soap_objective: str = "",
                        soap_assessment: str = "", soap_plan: str = "") -> str:
    """
    Save a patient visit record to the database.
    Use this to persist a patient's transcript and SOAP note.

    Args:
        patient_name: The patient's full name.
        transcript: The full transcript text.
        soap_subjective: Subjective section of the SOAP note.
        soap_objective: Objective section.
        soap_assessment: Assessment section.
        soap_plan: Plan section.

    Returns:
        Confirmation message with patient and session IDs.
    """
    # Find or create patient
    patient = get_patient_by_name(patient_name)
    if patient:
        patient_id = patient["id"]
    else:
        patient_id = create_patient(patient_name)

    # Create session
    soap = {
        "subjective": soap_subjective,
        "objective": soap_objective,
        "assessment": soap_assessment,
        "plan": soap_plan,
    }
    session_id = create_session(patient_id, transcript=transcript, soap_note=soap)

    return f"Record saved. Patient ID: {patient_id}, Session ID: {session_id}"


# ── Tool 5: Fetch Patient History ─────────────────────────────────────────────

@tool
def fetch_patient_history(patient_name: str) -> str:
    """
    Retrieve the full medical history of a patient.
    Use this to get context about a patient's previous visits, diagnoses,
    medications, and treatment plans.

    Args:
        patient_name: The patient's name to search for.

    Returns:
        A formatted summary of the patient's medical history.
    """
    patient = get_patient_by_name(patient_name)
    if not patient:
        return f"No patient found with name matching '{patient_name}'."

    history = get_patient_history(patient["id"])
    return history


# ── All tools list (for agent use) ─────────────────────────────────────────────

ALL_TOOLS = [
    transcribe_audio,
    generate_soap,
    validate_note,
    save_patient_record,
    fetch_patient_history,
]

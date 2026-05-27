# clinical_workflow/state.py
"""
Workflow state schema.

LANGGRAPH CONCEPT — STATE:
    State is the SINGLE source of truth that flows through the graph.
    Every node reads from it and writes to it.

    Think of it like a medical chart being passed between departments:
    - Radiology writes the X-ray results
    - The doctor reads them and writes the diagnosis
    - The pharmacist reads the diagnosis and writes prescriptions
    Each department reads/writes to the SAME chart.

    We use TypedDict (not Pydantic) because LangGraph's StateGraph
    works most naturally with TypedDict. The graph engine handles
    merging state updates from each node automatically.

WHY NOT A REGULAR DICT:
    A plain dict has no type hints. You'd get runtime KeyError bugs.
    TypedDict gives you:
    - IDE autocomplete
    - Type checking
    - Documentation of what the state contains
    - Compile-time error detection
"""
from typing import TypedDict, Optional


class ClinicalWorkflowState(TypedDict, total=False):
    """
    State that flows through the clinical documentation workflow.

    total=False means all fields are optional. This is important because:
    - At START, only audio_path and patient_name are set
    - Each node adds more fields as the workflow progresses
    - By END, all fields should be populated

    Fields are grouped by pipeline stage for clarity.
    """

    # ── Inputs (set at workflow start) ─────────────────────────────────────
    audio_path: str          # Path to the doctor's audio recording
    patient_name: str        # Patient's name for database lookup

    # ── Transcription (set by transcriber node) ────────────────────────────
    raw_transcript: str      # Raw text from Whisper
    clean_transcript: str    # Cleaned text (filler words removed)

    # ── SOAP Note (set by soap_formatter node) ─────────────────────────────
    soap_subjective: str     # S — what the patient reports
    soap_objective: str      # O — clinical observations
    soap_assessment: str     # A — diagnosis / impression
    soap_plan: str           # P — treatment plan

    # ── Validation (set by validator node) ─────────────────────────────────
    is_valid: bool                       # True if all SOAP sections filled
    missing_sections: list[str]          # Names of empty sections
    validation_warnings: list[str]       # Quality warnings
    retry_count: int                     # Number of SOAP formatting retries

    # ── Medical Entities (set by entity extractor in soap_formatter) ───────
    conditions: list[str]
    medications: list[str]
    allergies: list[str]
    symptoms: list[str]

    # ── Doctor Approval (set by approval node) ─────────────────────────────
    doctor_approved: Optional[bool]      # None=pending, True/False=decided
    doctor_feedback: str                 # Feedback text if rejected

    # ── Output (set by saver node) ─────────────────────────────────────────
    patient_id: Optional[int]            # Database patient ID
    session_id: Optional[int]            # Database session ID
    final_status: str                    # "saved" / "incomplete" / "corrected"

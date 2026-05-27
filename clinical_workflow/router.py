# clinical_workflow/router.py
"""
FastAPI router for the Stage 4 Clinical Documentation Workflow (LangGraph).

Exposes endpoints to start the workflow and review/approve generated SOAP notes.
"""
import os
import uuid
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver

from clinical_workflow.graph import build_clinical_workflow

logger = logging.getLogger("workflow.router")

router = APIRouter(prefix="/api/workflow", tags=["clinical-workflow"])

# In-memory checkpointer for clinical workflow state tracking
checkpointer = MemorySaver()
# Compile the clinical workflow graph with state history and a pause before doctor approval
workflow_app = build_clinical_workflow().compile(
    checkpointer=checkpointer,
    interrupt_before=["approval"]
)

# Upload directory setup
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class WorkflowStateResponse(BaseModel):
    """Response payload enclosing session state."""
    thread_id: str
    status: str  # "pending_approval" or "completed"
    state: dict


class ReviewRequest(BaseModel):
    """Payload to submit doctor approval/correction reviews."""
    thread_id: str
    approve: bool
    feedback: Optional[str] = ""
    soap_subjective: Optional[str] = None
    soap_objective: Optional[str] = None
    soap_assessment: Optional[str] = None
    soap_plan: Optional[str] = None


@router.post("/start", response_model=WorkflowStateResponse)
async def start_workflow(
    patient_name: str = Form(...),
    raw_transcript: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Start the clinical documentation workflow.

    Accepts:
    - patient_name: Name of the patient (for DB records).
    - raw_transcript: Optional text transcript of the consultation.
    - file: Optional audio recording of the consultation.

    Either `raw_transcript` or `file` must be provided.
    """
    if not raw_transcript and not file:
        raise HTTPException(
            status_code=400,
            detail="Either raw_transcript or an audio file must be provided."
        )

    audio_path = ""
    if file:
        ext = Path(file.filename).suffix.lower()
        allowed_exts = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {ext}. Allowed: {allowed_exts}"
            )

        filename = f"{uuid.uuid4()}_{file.filename}"
        audio_path = str(UPLOAD_DIR / filename)
        try:
            contents = await file.read()
            with open(audio_path, "wb") as f:
                f.write(contents)
            logger.info("Saved audio upload to %s", audio_path)
        except Exception as e:
            logger.error("Failed to write audio file: %s", e)
            raise HTTPException(status_code=500, detail="Failed to save uploaded audio file.")

    # Unique thread ID for tracking this specific patient session in LangGraph memory
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "audio_path": audio_path,
        "patient_name": patient_name,
        "raw_transcript": raw_transcript or "",
        "retry_count": 0,
    }

    logger.info("Initializing workflow thread %s for %s", thread_id, patient_name)
    try:
        # Executes graph until it reaches the approval node (interrupted)
        workflow_app.invoke(initial_state, config)
        
        # Extract the state values
        state_info = workflow_app.get_state(config)
        return WorkflowStateResponse(
            thread_id=thread_id,
            status="pending_approval",
            state=state_info.values
        )
    except Exception as e:
        logger.error("Workflow failed on thread %s: %s", thread_id, e, exc_info=True)
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.post("/review", response_model=WorkflowStateResponse)
async def review_workflow(request: ReviewRequest):
    """
    Approve or reject/correct the generated SOAP note.

    If approved:
    - Persists the record to SQLite and marks status as "completed".

    If rejected:
    - Feeds feedback into the correction loop.
    - Re-runs the generator/validation.
    - Interrupts again at the approval step, returning status "pending_approval" with changes.
    """
    thread_id = request.thread_id
    config = {"configurable": {"thread_id": thread_id}}

    state_info = workflow_app.get_state(config)
    if not state_info or not state_info.values:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow session thread '{thread_id}' not found."
        )

    # If the thread is already completed, return its final state
    if not state_info.next:
        return WorkflowStateResponse(
            thread_id=thread_id,
            status="completed",
            state=state_info.values
        )

    logger.info("Submitting review for thread %s: approved=%s", thread_id, request.approve)
    try:
        # Build update state dictionary
        state_update = {
            "doctor_approved": request.approve,
            "doctor_feedback": request.feedback or ""
        }
        if request.soap_subjective is not None:
            state_update["soap_subjective"] = request.soap_subjective
        if request.soap_objective is not None:
            state_update["soap_objective"] = request.soap_objective
        if request.soap_assessment is not None:
            state_update["soap_assessment"] = request.soap_assessment
        if request.soap_plan is not None:
            state_update["soap_plan"] = request.soap_plan

        # Write doctor's decision and edits directly into the LangGraph state channel
        workflow_app.update_state(config, state_update)

        # Resume graph execution (will execute approval node and route accordingly)
        workflow_app.invoke(None, config)

        # Retrieve updated state
        updated_state_info = workflow_app.get_state(config)
        updated_state = updated_state_info.values

        status = "completed" if not updated_state_info.next else "pending_approval"

        return WorkflowStateResponse(
            thread_id=thread_id,
            status=status,
            state=updated_state
        )
    except Exception as e:
        logger.error("Failed to submit review for thread %s: %s", thread_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to submit review: {str(e)}")

# clinical_workflow/router.py
"""
FastAPI router for the Clinical Documentation Workflow (LangGraph).

Exposes endpoints to start the workflow and review/approve generated SOAP notes.
The Gemini API key is injected at runtime via the X-Gemini-API-Key request header,
so it never needs to be stored in .env files or server configuration.
"""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Form, Header, HTTPException
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
    x_gemini_api_key: Optional[str] = Header(None),
):
    """
    Start the clinical documentation workflow.

    Accepts:
    - patient_name: Name of the patient (for DB records).
    - raw_transcript: Text transcript of the consultation.
    - X-Gemini-API-Key: Gemini API key passed from the UI at runtime.

    The transcript is required.
    """
    if not raw_transcript or not raw_transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="raw_transcript is required. Audio upload is not supported in v1.0."
        )

    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
            "api_key": x_gemini_api_key,
        }
    }

    initial_state = {
        "patient_name": patient_name,
        "raw_transcript": raw_transcript.strip(),
        "retry_count": 0,
    }

    logger.info("Initializing workflow thread %s for %s", thread_id, patient_name)
    try:
        workflow_app.invoke(initial_state, config)
        state_info = workflow_app.get_state(config)
        return WorkflowStateResponse(
            thread_id=thread_id,
            status="pending_approval",
            state=state_info.values
        )
    except Exception as e:
        logger.error("Workflow failed on thread %s: %s", thread_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.post("/review", response_model=WorkflowStateResponse)
async def review_workflow(
    request: ReviewRequest,
    x_gemini_api_key: Optional[str] = Header(None),
):
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
    config = {
        "configurable": {
            "thread_id": thread_id,
            "api_key": x_gemini_api_key,
        }
    }

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

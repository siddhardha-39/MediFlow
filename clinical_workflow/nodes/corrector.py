# clinical_workflow/nodes/corrector.py
"""
Node: Handle doctor rejection and re-generate specific SOAP sections.

LANGGRAPH CONCEPT — CORRECTION WORKFLOW:
    When the doctor rejects a note, they give feedback like:
    "The assessment section is wrong, the patient has GERD not IBS"

    This node:
    1. Reads the doctor's feedback
    2. Re-generates the SOAP note with the feedback as extra context
    3. Routes back to the validator to re-check

    This creates a LOOP in the graph:
    corrector -> validator -> (if valid) -> approval -> (if rejected) -> corrector

    We use retry_count to prevent infinite loops.
"""
import logging
from langchain_core.messages import HumanMessage

from config import MEDIFLOW_LLM_MODEL
from llm_factory import get_chat_llm
from clinical_workflow.state import ClinicalWorkflowState
from clinical_workflow.utils import parse_llm_json

logger = logging.getLogger("workflow.node.corrector")

llm = get_chat_llm(temperature=0.0)

MAX_CORRECTIONS = 3  # Safety limit to prevent infinite reject→correct loops

CORRECTION_PROMPT = """You are a medical documentation assistant.

Here is the current SOAP note:
Subjective: {subjective}
Objective: {objective}
Assessment: {assessment}
Plan: {plan}

The doctor rejected this note with the following feedback:
"{feedback}"

Please regenerate the SOAP note incorporating the doctor's feedback.
Return ONLY valid JSON with keys: subjective, objective, assessment, plan.
Do not include any explanation outside the JSON."""


def corrector_node(state: ClinicalWorkflowState) -> dict:
    """
    Re-generate SOAP note based on doctor feedback.

    Reads:  state["soap_*"], state["doctor_feedback"], state["retry_count"]
    Writes: state["soap_*"], state["doctor_approved"] (reset to None)
    """
    feedback = state.get("doctor_feedback", "No specific feedback")
    retry_count = state.get("retry_count", 0)
    logger.info("CORRECTOR: Processing feedback (attempt %d) - %s", retry_count, feedback)

    # Safety: prevent infinite correction loops
    if retry_count >= MAX_CORRECTIONS:
        logger.warning("CORRECTOR: Max corrections (%d) reached, keeping original", MAX_CORRECTIONS)
        return {"doctor_approved": None, "final_status": "max_corrections_reached"}

    prompt = CORRECTION_PROMPT.format(
        subjective=state.get("soap_subjective", ""),
        objective=state.get("soap_objective", ""),
        assessment=state.get("soap_assessment", ""),
        plan=state.get("soap_plan", ""),
        feedback=feedback,
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        data = parse_llm_json(raw)

        if data:
            logger.info("CORRECTOR: Regenerated SOAP note successfully")
            return {
                "soap_subjective": data.get("subjective", state.get("soap_subjective", "")),
                "soap_objective": data.get("objective", state.get("soap_objective", "")),
                "soap_assessment": data.get("assessment", state.get("soap_assessment", "")),
                "soap_plan": data.get("plan", state.get("soap_plan", "")),
                "doctor_approved": None,  # Reset approval for re-review
                "retry_count": retry_count + 1,
                "final_status": "corrected",
            }
    except Exception as e:
        logger.error("CORRECTOR: Failed - %s", e)

    # If correction fails, keep the original note
    logger.warning("CORRECTOR: Could not parse correction, keeping original")
    return {"doctor_approved": None, "final_status": "correction_failed"}

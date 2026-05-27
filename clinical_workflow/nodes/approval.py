# clinical_workflow/nodes/approval.py
"""
Node: Human-in-the-loop doctor approval.

LANGGRAPH CONCEPT — HUMAN-IN-THE-LOOP:
    Most AI workflows need a human checkpoint.
    In clinical documentation, this is CRITICAL:
    - AI generates the SOAP note
    - But a DOCTOR must approve it before it's saved
    - If the doctor rejects it, the workflow routes to correction

    In production, this would be a web UI or mobile app.
    For now, we use terminal input (input() function).

    LangGraph supports proper human-in-the-loop via interrupts,
    but for simplicity we use a blocking input() call.
    The concept is the same: the workflow PAUSES and waits for human input.
"""
import logging
from clinical_workflow.state import ClinicalWorkflowState

logger = logging.getLogger("workflow.node.approval")


def approval_node(state: ClinicalWorkflowState) -> dict:
    """
    Present SOAP note to doctor and ask for approval.

    Reads:  state["soap_*"], state["is_valid"], state["missing_sections"]
    Writes: state["doctor_approved"], state["doctor_feedback"]
    """
    # API / Non-interactive Mode bypass: if doctor_approved is already set, do not prompt
    if state.get("doctor_approved") is not None:
        logger.info("APPROVAL: Doctor decision pre-set to %s", state["doctor_approved"])
        return {
            "doctor_approved": state["doctor_approved"],
            "doctor_feedback": state.get("doctor_feedback", ""),
        }
    # Display the SOAP note for review
    print("\n" + "=" * 60)
    print("  SOAP NOTE FOR REVIEW")
    print("=" * 60)
    print(f"  Patient: {state.get('patient_name', 'Unknown')}")
    print("-" * 60)
    print(f"\n  [S] SUBJECTIVE:")
    print(f"  {state.get('soap_subjective', '(empty)')}")
    print(f"\n  [O] OBJECTIVE:")
    print(f"  {state.get('soap_objective', '(empty)')}")
    print(f"\n  [A] ASSESSMENT:")
    print(f"  {state.get('soap_assessment', '(empty)')}")
    print(f"\n  [P] PLAN:")
    print(f"  {state.get('soap_plan', '(empty)')}")

    # Show validation status
    if not state.get("is_valid", False):
        missing = state.get("missing_sections", [])
        print(f"\n  ** WARNING: Missing sections: {', '.join(missing)} **")

    warnings = state.get("validation_warnings", [])
    if warnings:
        for w in warnings:
            print(f"  ** {w} **")

    # Show extracted entities
    meds = state.get("medications", [])
    allergies = state.get("allergies", [])
    symptoms = state.get("symptoms", [])
    if meds or allergies or symptoms:
        print(f"\n  Extracted Entities:")
        if meds:
            print(f"    Medications: {', '.join(meds)}")
        if allergies:
            print(f"    Allergies: {', '.join(allergies)}")
        if symptoms:
            print(f"    Symptoms: {', '.join(symptoms)}")

    print("\n" + "=" * 60)

    # Ask for approval
    while True:
        choice = input("  Approve this note? (yes/no): ").strip().lower()
        if choice in ("yes", "y"):
            logger.info("APPROVAL: Doctor APPROVED the note")
            return {"doctor_approved": True, "doctor_feedback": ""}
        elif choice in ("no", "n"):
            feedback = input("  Reason for rejection: ").strip()
            logger.info("APPROVAL: Doctor REJECTED - %s", feedback)
            return {"doctor_approved": False, "doctor_feedback": feedback}
        else:
            print("  Please enter 'yes' or 'no'.")

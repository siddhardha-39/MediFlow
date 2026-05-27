# clinical_workflow/nodes/validator.py
"""
Node: Validate the SOAP note for completeness.

LANGGRAPH CONCEPT — CONDITIONAL ROUTING SETUP:
    This node sets state["is_valid"] which the conditional edge reads.
    The node itself doesn't decide where to go next — it just sets the flag.
    The GRAPH decides the routing based on the flag value.

    Separation of concerns:
    - Node: "Is this valid? Yes/No"
    - Graph edge: "If No, go to retry. If Yes, go to approval."
"""
import logging
from clinical_workflow.state import ClinicalWorkflowState

logger = logging.getLogger("workflow.node.validator")

MIN_SECTION_LENGTH = 10


def validator_node(state: ClinicalWorkflowState) -> dict:
    """
    Validate SOAP note completeness.

    Reads:  state["soap_*"] fields
    Writes: state["is_valid"], state["missing_sections"], state["validation_warnings"]
    """
    sections = {
        "Subjective": state.get("soap_subjective", ""),
        "Objective": state.get("soap_objective", ""),
        "Assessment": state.get("soap_assessment", ""),
        "Plan": state.get("soap_plan", ""),
    }

    missing = []
    warnings = []

    for name, content in sections.items():
        if not content or not content.strip():
            missing.append(name)
        elif len(content.strip()) < MIN_SECTION_LENGTH:
            warnings.append(f"{name} is very short ({len(content.strip())} chars)")
        elif content.strip().lower() in ("not documented in this visit", "n/a", "none"):
            warnings.append(f"{name} has no clinical content")

    is_valid = len(missing) == 0

    logger.info(
        "VALIDATOR: valid=%s, missing=%s, warnings=%d, retry_count=%d",
        is_valid, missing, len(warnings), state.get("retry_count", 0),
    )

    return {
        "is_valid": is_valid,
        "missing_sections": missing,
        "validation_warnings": warnings,
    }

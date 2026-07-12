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
from clinical_workflow.languagetool import check_text

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

    # ── LanguageTool Integration ──────────────────────────────────────────────
    prev_checked = state.get("languagetool_checked_sections", {}) or {}
    prev_warnings = state.get("languagetool_warnings", []) or []

    new_checked = dict(prev_checked)
    new_warnings = []
    lt_status = {"success": True}

    for name, content in sections.items():
        if not content or not content.strip():
            continue

        current_text = content.strip()
        prev_text = prev_checked.get(name)

        if prev_text == current_text:
            logger.info("VALIDATOR: Section %s is unchanged. Reusing LanguageTool results.", name)
            # Reuse previous warnings for this section
            section_warnings = [w for w in prev_warnings if w.get("section") == name]
            new_warnings.extend(section_warnings)
        else:
            logger.info("VALIDATOR: Section %s is new or changed. Running LanguageTool check.", name)
            result = check_text(current_text)
            if result.success:
                for w in result.warnings:
                    new_warnings.append({"section": name, **w.model_dump()})
                new_checked[name] = current_text
            else:
                lt_status = {
                    "success": False,
                    "error_type": result.error_type,
                    "error_detail": result.error_detail,
                }
                # Keep previously cached text if any so we retry on changes

    logger.info(
        "VALIDATOR: valid=%s, missing=%s, warnings=%d, lt_warnings=%d, lt_success=%s, retry_count=%d",
        is_valid, missing, len(warnings), len(new_warnings), lt_status["success"], state.get("retry_count", 0),
    )

    return {
        "is_valid": is_valid,
        "missing_sections": missing,
        "validation_warnings": warnings,
        "languagetool_warnings": new_warnings,
        "languagetool_status": lt_status,
        "languagetool_checked_sections": new_checked,
    }

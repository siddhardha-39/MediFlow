# clinical_workflow/graph.py
"""
LangGraph workflow definition — THE CORE OF STAGE 4.

LANGGRAPH CONCEPT — STATEGRAPH:
    A StateGraph is a directed graph where:
    - Nodes are functions
    - Edges connect nodes
    - State flows through the graph
    - Conditional edges enable branching

    Building a graph has 4 steps:
    1. Define the state schema (state.py - done)
    2. Create the graph: StateGraph(MyState)
    3. Add nodes: graph.add_node("name", function)
    4. Add edges: graph.add_edge("from", "to")
       or conditional: graph.add_conditional_edges("from", router_func, mapping)
    5. Set entry point: graph.set_entry_point("first_node")
    6. Compile: workflow = graph.compile()
    7. Run: result = workflow.invoke(initial_state)

GRAPH STRUCTURE:

    START
      |
      v
    [transcriber] ──> [cleaner] ──> [soap_formatter] ──> [validator]
                                                              |
                                          ┌───────────────────┤
                                          |                   |
                                     is_valid?           not valid?
                                          |                   |
                                          v                   v
                                     [approval]        [soap_formatter] (retry)
                                          |             (if retries < 3)
                                    ┌─────┤                  OR
                                    |     |              [approval]
                              approved? rejected?        (if retries >= 3)
                                    |     |
                                    v     v
                                [saver] [corrector] ──> [validator] (loop back)
                                    |
                                    v
                                   END
"""
import logging
from langgraph.graph import StateGraph, END

from clinical_workflow.state import ClinicalWorkflowState
from clinical_workflow.nodes.transcriber import transcriber_node
from clinical_workflow.nodes.cleaner import cleaner_node
from clinical_workflow.nodes.soap_formatter import soap_formatter_node
from clinical_workflow.nodes.validator import validator_node
from clinical_workflow.nodes.approval import approval_node
from clinical_workflow.nodes.saver import saver_node
from clinical_workflow.nodes.corrector import corrector_node

logger = logging.getLogger("workflow.graph")

MAX_FORMAT_RETRIES = 3  # Max SOAP formatting attempts before going to approval anyway


# ── Conditional Edge Functions ─────────────────────────────────────────────────
# These functions read the state and return a STRING that maps to the next node.

def after_validation(state: ClinicalWorkflowState) -> str:
    """
    CONDITIONAL EDGE: After validation, decide where to go.

    Logic:
        - Valid note? -> ask the doctor to approve it
        - Invalid AND retries left? -> try formatting again
        - Invalid AND out of retries? -> show it to the doctor anyway
    """
    is_valid = state.get("is_valid", False)
    retry_count = state.get("retry_count", 0)

    if is_valid:
        logger.info("ROUTING: Valid note -> approval")
        return "approval"
    elif retry_count < MAX_FORMAT_RETRIES:
        logger.info("ROUTING: Invalid note, retry %d/%d -> soap_formatter",
                     retry_count, MAX_FORMAT_RETRIES)
        return "soap_formatter"
    else:
        logger.info("ROUTING: Invalid note, max retries reached -> approval (with warnings)")
        return "approval"


def after_approval(state: ClinicalWorkflowState) -> str:
    """
    CONDITIONAL EDGE: After doctor approval, decide where to go.

    Logic:
        - Approved -> save to database
        - Rejected -> go to correction workflow
    """
    if state.get("doctor_approved", False):
        logger.info("ROUTING: Approved -> saver")
        return "saver"
    else:
        logger.info("ROUTING: Rejected -> corrector")
        return "corrector"


# ── Build the Graph ────────────────────────────────────────────────────────────

def build_clinical_workflow() -> StateGraph:
    """
    Construct the clinical documentation workflow graph.

    Returns a compiled graph ready to invoke.
    """
    graph = StateGraph(ClinicalWorkflowState)

    # Step 1: Add all nodes
    graph.add_node("transcriber", transcriber_node)
    graph.add_node("cleaner", cleaner_node)
    graph.add_node("soap_formatter", soap_formatter_node)
    graph.add_node("validator", validator_node)
    graph.add_node("approval", approval_node)
    graph.add_node("saver", saver_node)
    graph.add_node("corrector", corrector_node)

    # Step 2: Set the entry point (first node to run)
    graph.set_entry_point("transcriber")

    # Step 3: Add fixed edges (always go from A to B)
    graph.add_edge("transcriber", "cleaner")
    graph.add_edge("cleaner", "soap_formatter")
    graph.add_edge("soap_formatter", "validator")

    # Step 4: Add conditional edges
    # After validator: branch based on validation result
    graph.add_conditional_edges(
        "validator",           # Source node
        after_validation,      # Function that returns the next node name
        {                      # Mapping of return values to node names
            "approval": "approval",
            "soap_formatter": "soap_formatter",
        },
    )

    # After approval: branch based on doctor's decision
    graph.add_conditional_edges(
        "approval",
        after_approval,
        {
            "saver": "saver",
            "corrector": "corrector",
        },
    )

    # After corrector: check if max corrections reached
    def after_correction(state: ClinicalWorkflowState) -> str:
        """Route corrector output: continue validating or return for review."""
        if state.get("final_status") == "max_corrections_reached":
            logger.info("ROUTING: Max corrections reached -> approval for doctor decision")
            return "approval"    # Do not save a rejected note without explicit approval
        return "validator"       # Normal path: re-validate the corrected note

    graph.add_conditional_edges(
        "corrector",
        after_correction,
        {
            "validator": "validator",
            "approval": "approval",
        },
    )

    # After saver: workflow is done
    graph.add_edge("saver", END)

    logger.info("Clinical workflow graph built successfully")
    return graph


# ── Compiled Workflow ──────────────────────────────────────────────────────────
# Compile once, use everywhere
clinical_workflow = build_clinical_workflow().compile()

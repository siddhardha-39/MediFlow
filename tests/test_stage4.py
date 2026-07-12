# tests/test_stage4.py
"""
Automated test for Stage 4 LangGraph workflow.

Since the approval node uses input(), we can't test the full interactive
flow automatically. Instead we test:
1. Individual nodes
2. The graph structure
3. A non-interactive version (auto-approve)
"""
import sys
import os
import pytest

pytestmark = pytest.mark.unit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

SAMPLE_TRANSCRIPT = (
    "Doctor: Good morning Mr. Kumar, how are you feeling today? "
    "Patient: I've been having chest pain for the past two days. "
    "I also feel short of breath and some dizziness. "
    "Doctor: Are you taking your medications? "
    "Patient: Yes, amlodipine 5mg and metformin. I'm allergic to penicillin. "
    "Doctor: Blood pressure is 150/95. I'll order an ECG. "
    "Starting aspirin 75mg. Follow up in two weeks."
)


def print_section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def test_cleaner():
    """Test the cleaner node independently."""
    print_section("TEST 1: Cleaner Node")
    from clinical_workflow.nodes.cleaner import cleaner_node

    dirty = "So um the patient like has um chest pain you know and uh shortness of breath"
    state = {"raw_transcript": dirty}
    result = cleaner_node(state)
    cleaned = result["clean_transcript"]

    print(f"  Input:  {dirty}")
    print(f"  Output: {cleaned}")
    print(f"  Removed 'um': {'um' not in cleaned.lower()}")
    print(f"  Removed 'uh': {'uh' not in cleaned.lower()}")
    print("  [OK]")


def test_validator():
    """Test the validator node with complete and incomplete notes."""
    print_section("TEST 2: Validator Node")
    from clinical_workflow.nodes.validator import validator_node

    # Complete note
    state_good = {
        "soap_subjective": "Patient reports chest pain",
        "soap_objective": "Blood pressure 150/95",
        "soap_assessment": "Suspected angina",
        "soap_plan": "Order ECG, start aspirin",
    }
    result = validator_node(state_good)
    print(f"  Complete note: valid={result['is_valid']}, missing={result['missing_sections']}")
    assert result["is_valid"] == True, "Complete note should be valid"

    # Incomplete note
    state_bad = {
        "soap_subjective": "Patient reports chest pain",
        "soap_objective": "",
        "soap_assessment": "",
        "soap_plan": "Order ECG",
    }
    result = validator_node(state_bad)
    print(f"  Incomplete note: valid={result['is_valid']}, missing={result['missing_sections']}")
    assert result["is_valid"] == False, "Incomplete note should be invalid"
    assert "Objective" in result["missing_sections"]
    assert "Assessment" in result["missing_sections"]
    print("  [OK]")


def test_soap_formatter():
    """Test SOAP note generation."""
    print_section("TEST 3: SOAP Formatter Node")
    from clinical_workflow.nodes.soap_formatter import soap_formatter_node

    state = {"clean_transcript": SAMPLE_TRANSCRIPT, "retry_count": 0}
    result = soap_formatter_node(state)

    print(f"  Subjective: {result.get('soap_subjective', '')[:60]}...")
    print(f"  Objective:  {result.get('soap_objective', '')[:60]}...")
    print(f"  Assessment: {result.get('soap_assessment', '')[:60]}...")
    print(f"  Plan:       {result.get('soap_plan', '')[:60]}...")
    print(f"  Medications: {result.get('medications', [])}")
    print(f"  Allergies:   {result.get('allergies', [])}")
    print("  [OK]")


def test_graph_structure():
    """Test that the graph is built correctly."""
    print_section("TEST 4: Graph Structure")
    from clinical_workflow.graph import clinical_workflow

    # The compiled graph should exist
    print(f"  Graph compiled: {clinical_workflow is not None}")

    # Check node names
    node_names = list(clinical_workflow.get_graph().nodes.keys())
    expected = ["transcriber", "cleaner", "soap_formatter", "validator",
                "approval", "saver", "corrector"]
    # Filter out __start__ and __end__
    actual_nodes = [n for n in node_names if not n.startswith("__")]

    print(f"  Nodes: {actual_nodes}")
    for name in expected:
        assert name in actual_nodes, f"Missing node: {name}"
    print("  All expected nodes present.")
    print("  [OK]")


def test_auto_workflow():
    """
    Test the workflow with auto-approval by building a custom graph.

    WHY WE BUILD THE GRAPH MANUALLY:
        graph.py imports approval_node as a direct function reference.
        Monkey-patching the module attribute doesn't change the
        already-bound reference. So we build a fresh graph and
        inject our auto_approve function directly.
    """
    print_section("TEST 5: Full Workflow (auto-approve)")
    from langgraph.graph import StateGraph, END
    from clinical_workflow.state import ClinicalWorkflowState
    from clinical_workflow.nodes.transcriber import transcriber_node
    from clinical_workflow.nodes.cleaner import cleaner_node
    from clinical_workflow.nodes.soap_formatter import soap_formatter_node
    from clinical_workflow.nodes.validator import validator_node
    from clinical_workflow.nodes.saver import saver_node
    from clinical_workflow.nodes.corrector import corrector_node
    from clinical_workflow.graph import after_validation, after_approval

    def auto_approve(state):
        print("  [AUTO-APPROVE] Skipping interactive approval")
        return {"doctor_approved": True, "doctor_feedback": ""}

    # Build a fresh graph with our auto_approve in place of approval_node
    graph = StateGraph(ClinicalWorkflowState)
    graph.add_node("transcriber", transcriber_node)
    graph.add_node("cleaner", cleaner_node)
    graph.add_node("soap_formatter", soap_formatter_node)
    graph.add_node("validator", validator_node)
    graph.add_node("approval", auto_approve)       # <-- injected
    graph.add_node("saver", saver_node)
    graph.add_node("corrector", corrector_node)

    graph.set_entry_point("transcriber")
    graph.add_edge("transcriber", "cleaner")
    graph.add_edge("cleaner", "soap_formatter")
    graph.add_edge("soap_formatter", "validator")
    graph.add_conditional_edges("validator", after_validation, {
        "approval": "approval",
        "soap_formatter": "soap_formatter",
    })
    graph.add_conditional_edges("approval", after_approval, {
        "saver": "saver",
        "corrector": "corrector",
    })

    # Corrector conditional: bail out on max corrections, else re-validate
    def after_correction(state):
        if state.get("final_status") == "max_corrections_reached":
            return "saver"
        return "validator"

    graph.add_conditional_edges("corrector", after_correction, {
        "validator": "validator",
        "saver": "saver",
    })
    graph.add_edge("saver", END)

    auto_workflow = graph.compile()

    # Initialize database
    from database.db import init_db
    init_db()

    # Run workflow
    initial_state = {
        "audio_path": "",
        "patient_name": "Test Patient Stage4",
        "raw_transcript": SAMPLE_TRANSCRIPT,
        "retry_count": 0,
    }

    result = auto_workflow.invoke(initial_state)

    print(f"  Status:      {result.get('final_status')}")
    print(f"  Patient ID:  {result.get('patient_id')}")
    print(f"  Session ID:  {result.get('session_id')}")
    print(f"  Retries:     {result.get('retry_count')}")
    print(f"  Valid:        {result.get('is_valid')}")
    print(f"  Medications:  {result.get('medications')}")
    print(f"  Allergies:    {result.get('allergies')}")

    assert result.get("patient_id") is not None, "Should have saved patient"
    assert result.get("session_id") is not None, "Should have saved session"
    print("  [OK]")


def main():
    print("\n" + "=" * 60)
    print("  MediFlow Stage 4 - Automated Tests")
    print("=" * 60)

    test_cleaner()
    test_validator()
    test_soap_formatter()
    test_graph_structure()
    test_auto_workflow()

    print_section("SUMMARY")
    print("  Test 1 (Cleaner):        [OK]")
    print("  Test 2 (Validator):      [OK]")
    print("  Test 3 (SOAP Formatter): [OK]")
    print("  Test 4 (Graph):          [OK]")
    print("  Test 5 (Full Workflow):  [OK]")
    print("\n  All Stage 4 tests passed.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

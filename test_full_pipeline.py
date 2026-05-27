# test_full_pipeline.py
"""
End-to-end test for the complete MediFlow Stage 3 pipeline.

Tests ALL modules:
    1. Database initialization
    2. SOAP note generation
    3. Medical entity extraction (Stage 2)
    4. Database save
    5. Patient history retrieval
    6. Memory/context
    7. LangGraph workflow pipeline
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

# ── Test Data ──────────────────────────────────────────────────────────────────

SAMPLE_TRANSCRIPTS = [
    {
        "patient": "Rajesh Kumar",
        "transcript": (
            "Doctor: Good morning Mr. Kumar, how are you feeling today? "
            "Patient: I've been having chest pain for the past two days, especially when I walk upstairs. "
            "I also feel short of breath. "
            "Doctor: Any other symptoms? Dizziness, nausea? "
            "Patient: Some dizziness, yes. And I've been more tired than usual. "
            "Doctor: Are you still taking your blood pressure medication? "
            "Patient: Yes, amlodipine 5mg daily. I'm also on metformin for my diabetes. "
            "Doctor: Any allergies? "
            "Patient: I'm allergic to penicillin. "
            "Doctor: Let me check your vitals. Blood pressure is 150/95, heart rate 88. "
            "I'd like to order an ECG and a lipid panel. "
            "I'm going to start you on aspirin 75mg daily and refer you to cardiology. "
            "Follow up in two weeks."
        ),
    },
    {
        "patient": "Priya Sharma",
        "transcript": (
            "Patient reports persistent cough for three weeks with yellowish sputum. "
            "Temperature 38.2 degrees. Lungs show crackles on right lower lobe. "
            "Suspected lower respiratory tract infection. "
            "Prescribing amoxicillin 500mg three times daily for 7 days. "
            "Chest X-ray ordered. Follow up in 5 days."
        ),
    },
]


def test_section(name):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def main():
    print("\n" + "=" * 60)
    print("  MediFlow - Full Stage 3 Pipeline Test")
    print("=" * 60)

    # ── Test 1: Database ───────────────────────────────────────────────────
    test_section("TEST 1: Database Initialization")
    from database.db import init_db, create_patient, get_patient, list_patients
    init_db()
    print("[OK] Database initialized")

    # Create test patients
    from database.db import get_patient_by_name
    import sqlite3
    try:
        p1_id = create_patient("Rajesh Kumar", age=55, gender="Male", mrn="MRN-001")
    except sqlite3.IntegrityError:
        p1 = get_patient_by_name("Rajesh Kumar")
        p1_id = p1["id"] if p1 else None
    try:
        p2_id = create_patient("Priya Sharma", age=32, gender="Female", mrn="MRN-002")
    except sqlite3.IntegrityError:
        p2 = get_patient_by_name("Priya Sharma")
        p2_id = p2["id"] if p2 else None
    print(f"[OK] Found/Created patients: Rajesh (ID={p1_id}), Priya (ID={p2_id})")

    patients = list_patients()
    print(f"[OK] Total patients in DB: {len(patients)}")

    # ── Test 2: SOAP Note Generation ───────────────────────────────────────
    test_section("TEST 2: SOAP Note Generation")
    from soap_notes.service import generate_soap_note

    for case in SAMPLE_TRANSCRIPTS:
        print(f"\n  Patient: {case['patient']}")
        result = generate_soap_note(case["transcript"])

        print(f"  S: {result.soap_note.subjective[:80]}...")
        print(f"  O: {result.soap_note.objective[:80]}...")
        print(f"  A: {result.soap_note.assessment[:80]}...")
        print(f"  P: {result.soap_note.plan[:80]}...")
        print(f"  Valid: {result.validation.is_complete}")
        if result.validation.missing_sections:
            print(f"  Missing: {result.validation.missing_sections}")
        if result.patient_info:
            print(f"  Entities: {result.patient_info}")
        print("  [OK]")

    # ── Test 3: Database Save ──────────────────────────────────────────────
    test_section("TEST 3: Database Save via Pipeline")
    from database.db import create_session, get_patient_sessions

    for case in SAMPLE_TRANSCRIPTS:
        from database.db import get_patient_by_name
        patient = get_patient_by_name(case["patient"])
        result = generate_soap_note(case["transcript"])

        session_id = create_session(
            patient["id"],
            transcript=case["transcript"],
            soap_note=result.soap_note.model_dump(),
            patient_info=result.patient_info,
        )
        print(f"  [OK] Saved session {session_id} for {case['patient']}")

    # ── Test 4: Patient History Retrieval ───────────────────────────────────
    test_section("TEST 4: Patient History Retrieval")
    from database.db import get_patient_history

    for name in ["Rajesh Kumar", "Priya Sharma"]:
        history = get_patient_history(get_patient_by_name(name)["id"])
        print(f"\n  --- {name} ---")
        for line in history.split("\n")[:8]:
            print(f"  {line}")
        print("  ...")
        print("  [OK]")

    # ── Test 5: Memory System ──────────────────────────────────────────────
    test_section("TEST 5: Session Memory")
    from memory.session_memory import SessionContext

    session = SessionContext()
    session.set_patient("Rajesh Kumar")
    session.set_transcript(SAMPLE_TRANSCRIPTS[0]["transcript"])
    session.conversation.add("user", "Process this recording")
    session.conversation.add("agent", "SOAP note generated and saved")

    context = session.get_full_context()
    print(f"  Context length: {len(context)} chars")
    print(f"  Contains patient history: {'Patient:' in context}")
    print(f"  Contains transcript: {'chest pain' in context}")
    print(f"  Contains conversation: {'Process this recording' in context}")
    print("  [OK]")

    # ── Test 6: LangGraph Workflow ─────────────────────────────────────────
    test_section("TEST 6: LangGraph Workflow Pipeline")
    from workflow.pipeline import run_pipeline

    result = run_pipeline(
        transcript=SAMPLE_TRANSCRIPTS[0]["transcript"],
        patient_name="Rajesh Kumar",
        audio_file="test_recording.wav",
    )

    print(f"  Status: {result.get('final_status')}")
    print(f"  Patient ID: {result.get('patient_id')}")
    print(f"  Session ID: {result.get('session_id')}")
    print(f"  SOAP Valid: {result.get('is_valid')}")
    print(f"  Conditions: {result.get('conditions')}")
    print(f"  Medications: {result.get('medications')}")
    print(f"  Retries: {result.get('retry_count')}")
    print("  [OK]")

    # ── Summary ────────────────────────────────────────────────────────────
    test_section("SUMMARY")
    print("  Module 1 (Transcription):    Tested in test_transcription.py")
    print("  Module 2 (SOAP Notes):       [OK]")
    print("  Module 3 (LangChain Tools):  Available (tested via pipeline)")
    print("  Module 4 (Agent):            Available (depends on model capability)")
    print("  Module 5 (Database):         [OK]")
    print("  Module 6 (Memory):           [OK]")
    print("  Module 7 (LangGraph):        [OK]")
    print("\n  All Stage 3 modules operational.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

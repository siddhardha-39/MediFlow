# clinical_workflow/runner.py
"""
CLI runner for the clinical documentation workflow.

HOW TO USE:
    # With a real audio file:
    python -m clinical_workflow.runner --audio path/to/recording.wav --patient "Rajesh Kumar"

    # With transcript text directly (skips transcription):
    python -m clinical_workflow.runner --text "Patient reports chest pain..." --patient "Rajesh Kumar"

    # Quick test with sample data:
    python -m clinical_workflow.runner --demo
"""
import sys
import os
import argparse
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

from clinical_workflow.graph import clinical_workflow

# Sample transcript for demo mode
DEMO_TRANSCRIPT = (
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
)


def main():
    parser = argparse.ArgumentParser(description="MediFlow Clinical Documentation Workflow")
    parser.add_argument("--audio", type=str, help="Path to audio file")
    parser.add_argument("--text", type=str, help="Transcript text (skips transcription)")
    parser.add_argument("--patient", type=str, default="Unknown Patient", help="Patient name")
    parser.add_argument("--demo", action="store_true", help="Run with sample data")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  MediFlow - Clinical Documentation Workflow")
    print("  Stage 4: LangGraph Pipeline")
    print("=" * 60)

    # Build initial state
    if args.demo:
        print("\n  Running in DEMO mode with sample transcript...")
        initial_state = {
            "audio_path": "",
            "patient_name": "Rajesh Kumar",
            "raw_transcript": DEMO_TRANSCRIPT,
            "retry_count": 0,
        }
    elif args.text:
        print(f"\n  Processing text input for patient: {args.patient}")
        initial_state = {
            "audio_path": "",
            "patient_name": args.patient,
            "raw_transcript": args.text,
            "retry_count": 0,
        }
    elif args.audio:
        print(f"\n  Processing audio: {args.audio}")
        print(f"  Patient: {args.patient}")
        initial_state = {
            "audio_path": args.audio,
            "patient_name": args.patient,
            "retry_count": 0,
        }
    else:
        parser.print_help()
        print("\n  Use --demo for a quick test run.")
        return

    # Run the workflow
    print("\n  Starting workflow...\n")
    result = clinical_workflow.invoke(initial_state)

    # Print final result
    print("\n" + "=" * 60)
    print("  WORKFLOW COMPLETE")
    print("=" * 60)
    print(f"  Status:      {result.get('final_status', 'unknown')}")
    print(f"  Patient ID:  {result.get('patient_id', 'N/A')}")
    print(f"  Session ID:  {result.get('session_id', 'N/A')}")
    print(f"  Retries:     {result.get('retry_count', 0)}")
    print(f"  Approved:    {result.get('doctor_approved', 'N/A')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

# test_pipeline.py
"""
Full end-to-end pipeline test.

Pipeline:
    Patient Text
        ↓ extractor.py
    Raw LLM Output
        ↓ parser.py
    Python Dict
        ↓ validator.py
    PatientInfo (Pydantic)
        ↓ retry_handler.py  (wraps the above with retry logic)
    ExtractionResult
        ↓ confidence.py
    ScoredPatientInfo
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from structured_outputs.retry_handler import run_with_retry
from structured_outputs.confidence import score
from structured_outputs.utils import get_logger

logger = get_logger("test_pipeline")

# ── Test cases ─────────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Case 1 - Normal",
        "text": "Patient has diabetes and takes metformin 500mg twice daily.",
    },
    {
        "name": "Case 2 - Multiple Conditions",
        "text": (
            "Patient reports asthma, hypertension, and chest pain. "
            "Currently on salbutamol inhaler and amlodipine 5mg. "
            "Allergic to aspirin."
        ),
    },
    {
        "name": "Case 3 - Missing Information",
        "text": "Patient feels tired.",
    },
    {
        "name": "Case 4 - Noisy Clinical Text",
        "text": "Hx of DM. Rx: Metformin BID. NKDA. C/o SOB and CP.",
    },
]


# ── Pretty printer ─────────────────────────────────────────────────────────────

def _print_result(case_name: str, result, scored) -> None:
    sep = "-" * 60
    print(f"\n{sep}")
    print(f"  {case_name}")
    print(sep)

    if result.success:
        print(f"  [OK] Extraction succeeded  (retries used: {result.retries_used})")
    else:
        print(f"  [FAIL] Extraction failed   (retries used: {result.retries_used})")
        print(f"         Error: {result.error}")

    if result.patient_info:
        pi = result.patient_info
        print(f"\n  PatientInfo (validated):")
        print(f"    conditions:  {pi.conditions}")
        print(f"    allergies:   {pi.allergies}")
        print(f"    medications: {pi.medications}")
        print(f"    symptoms:    {pi.symptoms}")

    if scored:
        print(f"\n  Confidence:")
        print(f"    overall:     {scored.overall_confidence:.2%}")
        for field in ["conditions", "allergies", "medications", "symptoms"]:
            entities = getattr(scored, field)
            if entities:
                for e in entities:
                    print(f"    {field[:-1]:12s}  '{e.value}'  -> {e.confidence:.2%}")

    print()


# ── Runner ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  MediFlow -- Structured Medical Extraction Pipeline")
    print("  Stage 2 Test Run")
    print("=" * 60)

    for case in TEST_CASES:
        logger.info("Running: %s", case["name"])

        # Full pipeline with retry
        result = run_with_retry(case["text"])

        # Confidence scoring (only if extraction succeeded)
        scored = None
        if result.success and result.patient_info:
            notes = f"Retries used: {result.retries_used}" if result.retries_used else ""
            scored = score(result.patient_info, notes=notes)
            result.scored_info = scored

        _print_result(case["name"], result, scored)

    print("=" * 60)
    print("  Pipeline test complete.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

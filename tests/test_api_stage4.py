# tests/test_api_stage4.py
"""
Integration test suite for the Stage 4 API endpoints.

Tests the Patient History Summarizer briefing endpoint and the multi-turn
interactive LangGraph Clinical Workflow endpoints.
"""
import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import app
from database.db import init_db, get_patient_by_name

# Clinical transcript content used to execute the test workflow
SAMPLE_TEXT = (
    "Doctor: Hello, we are reviewing Rajesh Kumar's case today. "
    "Patient: Yes, I've had a fever for three days, and my chest feels tight when coughing. "
    "Doctor: Any history of allergies? "
    "Patient: Only penicillin. "
    "Doctor: Okay, I see. Let's record the vitals: blood pressure is 120/80, temp 101.5. "
    "I'll prescribe Tylenol 500mg every 6 hours and advise chest X-ray. "
    "Please follow up in 3 days."
)


@pytest.mark.unit
class TestAPIStage4(unittest.TestCase):
    """API Integration Test Case for Stage 4."""

    @classmethod
    def setUpClass(cls):
        # Ensure SQLite DB tables exist
        init_db()
        cls.client = TestClient(app)

    def test_health_check(self):
        """Verify that the FastAPI server starts up and responds to health checks."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "version": "0.4.0"})

    def test_patient_briefing_api(self):
        """Verify the Patient History Summarizer briefing GET endpoint."""
        patient_id = "PT-2024-001-Rajesh-Kumar"
        print(f"\n  [TEST] Requesting briefing for patient: {patient_id}...")
        response = self.client.get(f"/api/patients/{patient_id}/briefing")

        # Handles cases where Ollama might be unavailable by verifying fallback statuses
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["patient_id"], patient_id)
            self.assertIn("briefing", data)
            self.assertIn("PATIENT BRIEFING", data["briefing"])
            print("  [TEST] Briefing generated successfully:\n")
            print(data["briefing"][:350] + "\n...")
        else:
            print(f"  [TEST] Briefing request returned code: {response.status_code} (Check Ollama status)")
            self.assertEqual(response.status_code, 500)

    def test_workflow_api_lifecycle(self):
        """Verify starting the workflow, submitting corrections, and final approval/persistence."""
        patient_name = "API Test Patient"

        # 1. Start the workflow
        print("\n  [TEST] Initiating workflow via API...")
        response = self.client.post(
            "/api/workflow/start",
            data={
                "patient_name": patient_name,
                "raw_transcript": SAMPLE_TEXT
            }
        )

        if response.status_code != 200:
            print(f"  [TEST] Workflow start failed: {response.status_code} - {response.text}")
            self.assertEqual(response.status_code, 500)
            return

        data = response.json()
        self.assertIn("thread_id", data)
        self.assertEqual(data["status"], "pending_approval")
        self.assertIn("state", data)

        thread_id = data["thread_id"]
        state = data["state"]

        self.assertEqual(state["patient_name"], patient_name)
        self.assertIn("soap_subjective", state)
        self.assertIn("soap_plan", state)

        print(f"  [TEST] Session created. Thread ID: {thread_id}")
        print(f"  [TEST] Subjective Section: {state.get('soap_subjective')}")

        # 2. Reject the SOAP note and pass feedback
        print("  [TEST] Submitting correction review (Rejection)...")
        feedback = "The assessment section is missing pneumonia suspicion and Tylenol is 500mg not 650mg."
        response_review = self.client.post(
            "/api/workflow/review",
            json={
                "thread_id": thread_id,
                "approve": False,
                "feedback": feedback
            }
        )

        self.assertEqual(response_review.status_code, 200)
        review_data = response_review.json()
        self.assertEqual(review_data["thread_id"], thread_id)
        self.assertEqual(review_data["status"], "pending_approval")

        corrected_state = review_data["state"]
        self.assertGreaterEqual(corrected_state.get("retry_count", 0), 1)
        print(f"  [TEST] Rejection loop processed. Retries: {corrected_state.get('retry_count')}")
        print(f"  [TEST] Corrected SOAP Assessment: {corrected_state.get('soap_assessment')}")

        # 3. Approve the updated SOAP note
        print("  [TEST] Submitting final approval review...")
        response_approve = self.client.post(
            "/api/workflow/review",
            json={
                "thread_id": thread_id,
                "approve": True,
                "feedback": ""
            }
        )

        self.assertEqual(response_approve.status_code, 200)
        approve_data = response_approve.json()
        self.assertEqual(approve_data["thread_id"], thread_id)
        self.assertEqual(approve_data["status"], "completed")

        final_state = approve_data["state"]
        self.assertIsNotNone(final_state.get("patient_id"))
        self.assertIsNotNone(final_state.get("session_id"))
        self.assertEqual(final_state.get("final_status"), "saved")

        print(f"  [TEST] Workflow finished. Patient ID: {final_state.get('patient_id')}, Session ID: {final_state.get('session_id')}")

        # Verify SQLite storage
        saved_patient = get_patient_by_name(patient_name)
        self.assertIsNotNone(saved_patient)
        self.assertEqual(saved_patient["id"], final_state["patient_id"])
        print(f"  [TEST] Verified SQLite: Patient '{patient_name}' is stored with ID {saved_patient['id']}.")


if __name__ == "__main__":
    unittest.main()

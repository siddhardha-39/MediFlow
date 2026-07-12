# tests/test_integration_docker.py
"""
Integration tests for PostgreSQL database and LanguageTool services running in Docker.

These tests run only if:
1. The environment variable MEDIFLOW_RUN_INTEGRATION_TESTS=1 is set.
2. The services are active and reachable.
"""
import os
import uuid
import pytest
import psycopg2
import httpx

import config
import database.db as db
from clinical_workflow.languagetool import check_text, LanguageToolCheckResult, LanguageToolWarning


def run_integration_guard():
    """Verify that the integration tests environment flag is enabled."""
    if os.getenv("MEDIFLOW_RUN_INTEGRATION_TESTS") != "1":
        pytest.skip("Integration tests disabled. Set MEDIFLOW_RUN_INTEGRATION_TESTS=1 to run.")


@pytest.mark.integration
def test_real_postgres_connection():
    """
    Verify PostgreSQL integration:
    - Application backend selection is PostgreSQL.
    - Schema initialization (init_db) succeeds.
    - Creating and retrieving a patient.
    - Saving and retrieving a session.
    - Database statistics updates.
    - Unique identifiers are cleaned up.
    """
    run_integration_guard()

    # 1. Verify backend selection is PostgreSQL
    if not config.IS_POSTGRES:
        pytest.skip("PostgreSQL is not configured as the active database backend in config.py.")

    # 2. Test Connection and Schema Initialization
    try:
        db.init_db()
    except Exception as e:
        pytest.fail(f"Failed to initialize PostgreSQL database: {e}")

    # Generate unique test data
    uid = uuid.uuid4().hex[:8]
    test_name = f"Synth Patient {uid}"
    test_mrn = f"MRN-SYNTH-{uid}"

    patient_id = None
    try:
        # 3. Create Patient
        patient_id = db.create_patient(
            name=test_name,
            age=45,
            gender="Male",
            medical_record_number=test_mrn
        )
        assert patient_id is not None
        assert patient_id > 0

        # 4. Retrieve Patient
        patient = db.get_patient(patient_id)
        assert patient is not None
        assert patient["name"] == test_name
        assert patient["medical_record_number"] == test_mrn

        # 5. Create Session
        soap = {
            "subjective": "Patient reports a sore throat.",
            "objective": "Tonsils are red.",
            "assessment": "Acute pharyngitis.",
            "plan": "Take rest and warm fluids."
        }
        entities = {
            "conditions": ["Pharyngitis"],
            "medications": [],
            "allergies": [],
            "symptoms": ["Sore throat"]
        }
        session_id = db.create_session(patient_id, soap_note=soap, patient_info=entities)
        assert session_id is not None
        assert session_id > 0

        # 6. Retrieve Session
        sessions = db.get_patient_sessions(patient_id)
        assert len(sessions) == 1
        assert sessions[0]["soap_subjective"] == soap["subjective"]
        assert sessions[0]["soap_assessment"] == soap["assessment"]

        # 7. Database Statistics
        stats = db.get_db_stats()
        assert stats["total_patients"] >= 1
        assert stats["total_sessions"] >= 1

    except Exception as e:
        pytest.fail(f"PostgreSQL integration flow failed: {e}")
    finally:
        # Cleanup test records to avoid database pollution
        if patient_id:
            try:
                conn = db._get_connection()
                cursor = conn.cursor()
                # Due to foreign key cascades, deleting the patient deletes associated sessions
                if db.IS_POSTGRES:
                    cursor.execute("DELETE FROM patients WHERE id = %s;", (patient_id,))
                else:
                    cursor.execute("DELETE FROM patients WHERE id = ?;", (patient_id,))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as cleanup_err:
                print(f"Warning: Integration test cleanup failed: {cleanup_err}")


@pytest.mark.integration
def test_real_languagetool_endpoint():
    """
    Verify LanguageTool integration:
    - Successful client call using clinical_workflow.languagetool.check_text.
    - Grammar warnings correctly parsed into structured model.
    - Replacements preserved.
    - Zero-match success distinguishable from failures.
    """
    run_integration_guard()

    if not config.MEDIFLOW_LANGUAGETOOL_URL:
        pytest.skip("LanguageTool URL is not configured.")

    # 1. Test text check with a known grammar mistake
    test_text = "This is an patient."
    try:
        result = check_text(test_text)
        assert result.success is True
        assert len(result.warnings) > 0
        
        # Verify warning structure
        warning = result.warnings[0]
        assert isinstance(warning, LanguageToolWarning)
        assert warning.matched_text == "an"
        assert len(warning.replacements) > 0
        assert "a" in warning.replacements

    except Exception as e:
        pytest.fail(f"LanguageTool integration check failed: {e}")

    # 2. Test clean text (zero matches check)
    try:
        clean_result = check_text("This is a patient.")
        assert clean_result.success is True
        assert len(clean_result.warnings) == 0
    except Exception as e:
        pytest.fail(f"LanguageTool clean text check failed: {e}")

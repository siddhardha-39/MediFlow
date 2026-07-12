# tests/conftest.py
"""
Pytest configuration, hooks, and global fixtures.
"""
from types import SimpleNamespace

import pytest


class _FakeLLM:
    def invoke(self, messages, *args, **kwargs):
        content = ""
        if messages:
            first = messages[0]
            content = getattr(first, "content", str(first))
        lower = content.lower()

        if "soap format" in lower or "return only valid json" in lower:
            return SimpleNamespace(
                content=(
                    '{"subjective":"Patient reports chest pain and shortness of breath.",'
                    '"objective":"Blood pressure 150/95 with mild distress noted.",'
                    '"assessment":"Possible acute cardiopulmonary issue requiring follow up.",'
                    '"plan":"Order ECG, continue aspirin, and arrange close review."}'
                )
            )

        if "regenerate the soap note" in lower or "the doctor rejected this note" in lower:
            return SimpleNamespace(
                content=(
                    '{"subjective":"Patient reports chest pain and shortness of breath.",'
                    '"objective":"Blood pressure 150/95 with mild distress noted.",'
                    '"assessment":"Possible acute cardiopulmonary issue requiring follow up.",'
                    '"plan":"Order ECG, continue aspirin, and arrange close review."}'
                )
            )

        return SimpleNamespace(content="Dashboard insights: the database is active and the mock LLM responded.")


@pytest.fixture(autouse=True)
def mock_llm_integrations(monkeypatch):
    from agents import Patient_history_summeriser as patient_summary_module
    from agents import router as agents_router
    from clinical_workflow.nodes import corrector as corrector_module
    from clinical_workflow.nodes import soap_formatter as soap_formatter_module

    def fake_get_chat_llm(*args, **kwargs):
        return _FakeLLM()

    monkeypatch.setattr("llm_factory.get_chat_llm", fake_get_chat_llm)
    monkeypatch.setattr(soap_formatter_module, "get_chat_llm", fake_get_chat_llm)
    monkeypatch.setattr(corrector_module, "get_chat_llm", fake_get_chat_llm)
    monkeypatch.setattr(agents_router, "get_chat_llm", fake_get_chat_llm)
    monkeypatch.setattr(patient_summary_module, "generate_grounded_patient_briefing", lambda *args, **kwargs: "PATIENT BRIEFING\n================\nName: Mock Patient\nAge: Unknown | Blood Group: Unknown\n\n[CRITICAL ALERTS]\n- None found\n\n[CHRONIC CONDITIONS]\n- Unknown\n\n[CURRENT MEDICATIONS]\n- Unknown\n\n[RECENT TESTS (KEY FINDINGS ONLY)]\n- Unknown\n\n[RECENT VISITS SUMMARY]\n- Unknown\n\n[DOCTOR'S FOCUS FOR TODAY]\n- Review source records before clinical decision-making.")
    monkeypatch.setattr(
        soap_formatter_module,
        "_extract_entities",
        lambda transcript, api_key=None: {
            "conditions": ["hypertension"],
            "medications": ["aspirin"],
            "allergies": ["penicillin"],
            "symptoms": ["chest pain"],
        },
    )


def pytest_collection_modifyitems(config, items):
    """
    Exclude integration tests from default runs.
    Integration tests only run when explicitly requested via '-m integration'.
    """
    markexpr = config.getoption("markexpr") or ""

    # Only exclude integration when no explicit integration filter is requested
    if markexpr == "" or markexpr == "unit":
        selected = []
        deselected = []
        for item in items:
            if "integration" in item.keywords:
                deselected.append(item)
            else:
                selected.append(item)
        items[:] = selected
        if deselected:
            config.hook.pytest_deselected(items=deselected)

# tests/conftest.py
"""
Pytest configuration, hooks, and global fixtures.
"""
import pytest
from unittest.mock import patch
from clinical_workflow.languagetool import LanguageToolCheckResult


def pytest_collection_modifyitems(config, items):
    """
    Hook to modify the collected tests dynamically:
    1. If the user explicitly requests integration tests (via '-m integration'),
       we deselect all other tests and run only integration tests.
    2. By default (plain 'pytest' or other markers), we exclude all integration
       tests from the run and deselect them.
    """
    markexpr = config.getoption("markexpr") or ""

    if "integration" in markexpr:
        # Keep only integration tests
        selected = []
        deselected = []
        for item in items:
            if "integration" in item.keywords:
                selected.append(item)
            else:
                deselected.append(item)
        items[:] = selected
        if deselected:
            config.hook.pytest_deselected(items=deselected)
    else:
        # Exclude integration tests by default
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


@pytest.fixture(autouse=True)
def mock_languagetool_validator_node(request):
    """
    Autouse fixture to mock LanguageTool check_text specifically for the validator node,
    preventing 5-second network connection timeouts during default unit test execution.

    It skips mocking if the test is marked with 'integration' or if the test is defined
    within 'tests/test_languagetool.py' to allow explicit client-level and node-level testing.
    """
    # 1. Skip mocking for integration tests
    if "integration" in request.keywords:
        yield
        return

    # 2. Skip mocking for LanguageTool test suite to allow custom mocked HTTP/failures testing
    if request.module and "test_languagetool" in request.module.__name__:
        yield
        return

    # 3. Apply mock for default workflow and API unit tests
    with patch("clinical_workflow.nodes.validator.check_text") as mock_check:
        mock_check.return_value = LanguageToolCheckResult(success=True, warnings=[])
        yield mock_check

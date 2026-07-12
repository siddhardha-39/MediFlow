# tests/conftest.py
"""
Pytest configuration, hooks, and global fixtures.
"""
import pytest


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

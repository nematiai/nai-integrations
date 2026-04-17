"""Pytest configuration for nai-integrations tests."""

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests in tests/ and apps/*/tests/ based on location.

    Rules:
    - tests/integration/mocked/*  → integration_mocked
    - tests/integration/live/*    → integration_live
    - everything else             → unit (default)
    """
    for item in items:
        path = str(item.fspath).replace("\\", "/")

        if "/tests/integration/live/" in path:
            item.add_marker(pytest.mark.integration_live)
        elif "/tests/integration/mocked/" in path:
            item.add_marker(pytest.mark.integration_mocked)
        else:
            item.add_marker(pytest.mark.unit)

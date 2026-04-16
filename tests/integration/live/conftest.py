"""Fixtures and guards specific to LIVE integration tests.

Live tests hit real vendor sandbox APIs. Safety rules:
- Tests are skipped if NEMI_TEST_ENV != 'live'
- Tests are skipped if required credentials are missing
- Developers must acquire sandbox accounts per .env.test.live.example
"""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip all live tests unless NEMI_TEST_ENV=live.

    Safety net: even if a developer accidentally runs
    `pytest -m integration_live` without setting the env,
    tests will be skipped rather than failing loudly or
    accidentally succeeding against the wrong endpoint.
    """
    if os.environ.get("NEMI_TEST_ENV", "").lower() == "live":
        return  # Allow live tests to run

    skip_live = pytest.mark.skip(
        reason="Live tests require NEMI_TEST_ENV=live and .env.test.live credentials"
    )
    for item in items:
        if "integration_live" in item.keywords:
            item.add_marker(skip_live)


def require_env(*var_names: str):
    """Return a decorator that skips a test if any required env var is missing.

    Usage:
        @require_env("TELEGRAM_BOT_TOKEN", "TELEGRAM_TEST_CHAT_ID")
        def test_telegram_live_post(...):
            ...
    """
    missing = [v for v in var_names if not os.environ.get(v)]
    reason = f"Missing required env vars: {', '.join(missing)}" if missing else ""
    return pytest.mark.skipif(bool(missing), reason=reason)

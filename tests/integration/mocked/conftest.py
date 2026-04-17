"""Fixtures specific to MOCKED integration tests.

Mocked tests use the `responses` library (for `requests`-based adapters)
and `respx` (for `httpx`-based adapters) to intercept HTTP calls.

No real network traffic occurs in this tier.
"""

import pytest
import respx
import responses as _responses


@pytest.fixture
def mock_requests():
    """Activate `responses` mocking for tests using the `requests` library.

    Usage:
        def test_something(mock_requests):
            mock_requests.add(
                mock_requests.POST,
                "https://api.example.com/endpoint",
                json={"ok": True},
                status=200,
            )
            # ... test code that calls requests.post(...)
    """
    with _responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_httpx():
    """Activate `respx` mocking for tests using the `httpx` library.

    Usage:
        def test_something(mock_httpx):
            mock_httpx.post("https://api.example.com/endpoint").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )
            # ... test code that calls httpx.post(...)
    """
    with respx.mock(assert_all_called=False) as mocker:
        yield mocker

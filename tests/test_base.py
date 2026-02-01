"""Tests for base classes."""

import pytest
from unittest.mock import MagicMock, patch


class TestBaseCloudAuth:
    def test_encrypt_decrypt_token(self):
        from nai_integrations.base.models import BaseCloudAuth
        original_token = "test_access_token_12345"
        encrypted = BaseCloudAuth._encrypt_token(original_token)
        decrypted = BaseCloudAuth._decrypt_token(encrypted)
        assert decrypted == original_token

    def test_encrypt_without_key_returns_original(self):
        from nai_integrations.base.models import BaseCloudAuth
        original_token = "test_token"
        with patch.object(BaseCloudAuth, '_get_encryption_key', return_value=None):
            encrypted = BaseCloudAuth._encrypt_token(original_token)
            assert encrypted == original_token


class TestBaseCloudService:
    def test_retry_api_call_success(self):
        from nai_integrations.base.services import BaseCloudService
        mock_func = MagicMock(return_value="success")
        result = BaseCloudService.retry_api_call(mock_func, max_retries=3)
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_api_call_with_retries(self):
        from nai_integrations.base.services import BaseCloudService
        import requests
        mock_func = MagicMock(side_effect=[
            requests.RequestException("fail"),
            requests.RequestException("fail"),
            "success"
        ])
        result = BaseCloudService.retry_api_call(mock_func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert mock_func.call_count == 3


class TestExceptions:
    def test_integration_error(self):
        from nai_integrations.base.exceptions import IntegrationError
        error = IntegrationError("Test error", code="TEST_CODE", details={"key": "value"})
        assert str(error) == "Test error"
        assert error.code == "TEST_CODE"
        assert error.details == {"key": "value"}

    def test_authentication_error(self):
        from nai_integrations.base.exceptions import AuthenticationError
        error = AuthenticationError()
        assert error.code == "AUTHENTICATION_ERROR"

    def test_token_refresh_error(self):
        from nai_integrations.base.exceptions import TokenRefreshError
        error = TokenRefreshError("Refresh failed")
        assert error.code == "TOKEN_REFRESH_ERROR"

    def test_api_error_with_status_code(self):
        from nai_integrations.base.exceptions import APIError
        error = APIError("API failed", status_code=401)
        assert error.code == "API_ERROR"
        assert error.status_code == 401

    def test_configuration_error(self):
        from nai_integrations.base.exceptions import ConfigurationError
        error = ConfigurationError("Missing config")
        assert error.code == "CONFIGURATION_ERROR"

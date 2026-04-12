"""Abstract base service for cloud storage integrations."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Callable, Dict, Optional, TypeVar

import requests
from django.utils import timezone

from apps.core.base.exceptions import APIError, TokenRefreshError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class BaseCloudService(ABC):
    """
    Abstract base class for cloud storage service operations.

    Receives app_client + external_user_id (not Django User).
    Provides OAuth flow, token management, and API requests with auto-refresh.
    """

    PROVIDER_NAME: str = "cloud"
    API_BASE_URL: str = ""
    AUTH_URL: str = ""
    TOKEN_URL: str = ""
    DEFAULT_TOKEN_EXPIRY: int = 3600

    def __init__(self, app_client: Any, external_user_id: str) -> None:
        self.app_client = app_client
        self.external_user_id = external_user_id
        self.auth = None
        self._load_auth()

    @abstractmethod
    def _load_auth(self) -> None:
        """Load authentication record for the app_client + external_user_id."""

    @abstractmethod
    def _get_auth_model(self) -> type:
        """Return the auth model class."""

    def is_connected(self) -> bool:
        return self.auth is not None and self.auth.is_active

    def get_connection_status(self) -> Dict[str, Any]:
        if not self.is_connected():
            return {
                "connected": False,
                "email": None,
                "display_name": None,
                "account_id": None,
                "connected_at": None,
            }
        return {
            "connected": True,
            "email": self.auth.email,
            "display_name": self.auth.display_name,
            "account_id": self.auth.account_id,
            "connected_at": self.auth.connected_at,
        }

    @abstractmethod
    def get_authorization_url(
        self, redirect_uri: str, state: Optional[str] = None
    ) -> str:
        """Generate OAuth authorization URL."""

    @abstractmethod
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""

    @abstractmethod
    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""

    def _ensure_valid_token(self) -> None:
        if not self.auth:
            raise APIError(f"{self.PROVIDER_NAME} not connected")
        if self.auth.needs_refresh():
            logger.info(
                "%s token needs refresh for %s:%s",
                self.PROVIDER_NAME,
                self.app_client.name,
                self.external_user_id,
            )
            if not self.refresh_access_token():
                raise TokenRefreshError(f"Failed to refresh {self.PROVIDER_NAME} token")

    def save_tokens(
        self,
        token_data: Dict[str, Any],
        account_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save or update tokens for the app_client + external_user_id."""
        expires_in = token_data.get("expires_in", self.DEFAULT_TOKEN_EXPIRY)
        expires_at = timezone.now() + timedelta(seconds=expires_in)

        defaults = {
            "token_type": token_data.get("token_type", "bearer"),
            "expires_at": expires_at,
            "is_active": True,
        }
        if account_info:
            defaults.update(self._extract_account_info(account_info))

        auth_model = self._get_auth_model()
        self.auth, created = auth_model.objects.update_or_create(
            app_client=self.app_client,
            external_user_id=self.external_user_id,
            defaults=defaults,
        )

        self.auth.decrypted_access_token = token_data["access_token"]
        if token_data.get("refresh_token"):
            self.auth.decrypted_refresh_token = token_data["refresh_token"]

        if "scope" in token_data:
            scope = token_data["scope"]
            self.auth.scopes = scope.split() if isinstance(scope, str) else scope

        self.auth.save()
        action = "created" if created else "updated"
        logger.info(
            "%s tokens %s for %s:%s",
            self.PROVIDER_NAME,
            action,
            self.app_client.name,
            self.external_user_id,
        )

    def _extract_account_info(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract account info into model fields. Override per provider."""
        return {
            "account_id": account_info.get("id", ""),
            "email": account_info.get("email", ""),
            "display_name": account_info.get("name", ""),
        }

    def disconnect(self) -> bool:
        if not self.auth:
            return True
        self._revoke_token()
        self.auth.is_active = False
        self.auth.save()
        logger.info(
            "%s disconnected for %s:%s",
            self.PROVIDER_NAME,
            self.app_client.name,
            self.external_user_id,
        )
        return True

    def _revoke_token(self) -> None:
        """Revoke token with provider. Override if supported."""

    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an authenticated API request with auto-refresh."""
        self._ensure_valid_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.auth.decrypted_access_token}"
        url = f"{base_url or self.API_BASE_URL}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method, url, headers=headers, timeout=30, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            detail = self._extract_error_detail(e.response)
            logger.error(
                "%s API error for %s:%s: %s",
                self.PROVIDER_NAME,
                self.app_client.name,
                self.external_user_id,
                detail,
            )
            raise APIError(
                f"{self.PROVIDER_NAME} API error: {detail}",
                status_code=e.response.status_code,
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                "%s request failed for %s:%s: %s",
                self.PROVIDER_NAME,
                self.app_client.name,
                self.external_user_id,
                e,
            )
            raise APIError(f"Request failed: {str(e)}")

    def _extract_error_detail(self, response: requests.Response) -> str:
        try:
            error_json = response.json()
            return error_json.get("error", {}).get("message", str(error_json))
        except Exception:
            return response.text if response.text else str(response.status_code)

    @staticmethod
    def retry_api_call(
        func: Callable[[], T],
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        retry_on: tuple = (
            requests.RequestException,
            ConnectionError,
            TimeoutError,
        ),
    ) -> T:
        """Retry an API call with exponential backoff."""
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return func()
            except retry_on as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (backoff_factor**attempt)
                    logger.warning(
                        "API call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt + 1,
                        max_retries + 1,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "API call failed after %d attempts: %s",
                        max_retries + 1,
                        e,
                    )
                    raise
            except Exception:
                raise
        raise last_exception  # type: ignore[misc]

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get current user's account information from provider."""

    @abstractmethod
    def list_folder(self, folder_id: str = None, **kwargs: Any) -> Dict[str, Any]:
        """List contents of a folder."""

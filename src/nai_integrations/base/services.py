"""
Abstract base service for cloud storage integrations.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Callable, Dict, Optional, TypeVar

import requests
from django.contrib.auth import get_user_model
from django.utils import timezone

from .exceptions import APIError, ConfigurationError, TokenRefreshError

logger = logging.getLogger(__name__)
User = get_user_model()
T = TypeVar('T')


class BaseCloudService(ABC):
    """
    Abstract base class for cloud storage service operations.
    
    Provides common functionality for OAuth flow, token management,
    and API requests with automatic token refresh.
    """

    # Override in subclasses
    PROVIDER_NAME: str = "cloud"
    API_BASE_URL: str = ""
    AUTH_URL: str = ""
    TOKEN_URL: str = ""
    
    # Default token expiry (1 hour)
    DEFAULT_TOKEN_EXPIRY: int = 3600

    def __init__(self, user: User):
        """
        Initialize the service for a specific user.
        
        Args:
            user: Django user instance
        """
        self.user = user
        self.auth = None
        self._load_auth()

    @abstractmethod
    def _load_auth(self) -> None:
        """Load authentication record for the user. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _get_auth_model(self):
        """Return the auth model class. Must be implemented by subclasses."""
        pass

    # =========================================================================
    # Connection Status
    # =========================================================================

    def is_connected(self) -> bool:
        """Check if user has connected this cloud storage."""
        return self.auth is not None and self.auth.is_active

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
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

    # =========================================================================
    # OAuth Flow
    # =========================================================================

    @abstractmethod
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL.
        
        Args:
            redirect_uri: URL to redirect to after authorization
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        pass

    @abstractmethod
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from provider
            redirect_uri: The same redirect URI used in authorization
            
        Returns:
            Token information dict
        """
        pass

    @abstractmethod
    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        pass

    # =========================================================================
    # Token Management
    # =========================================================================

    def _ensure_valid_token(self) -> None:
        """Ensure the access token is valid, refresh if needed."""
        if not self.auth:
            raise APIError(f"{self.PROVIDER_NAME} not connected")

        if self.auth.needs_refresh():
            logger.info(f"Token needs refresh for user {self.user.id}")
            if not self.refresh_access_token():
                raise TokenRefreshError(f"Failed to refresh {self.PROVIDER_NAME} token")

    def save_tokens(
        self,
        token_data: Dict[str, Any],
        account_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save or update tokens for the user.
        
        Args:
            token_data: Token data from OAuth response
            account_info: Optional account information
        """
        expires_in = token_data.get('expires_in', self.DEFAULT_TOKEN_EXPIRY)
        expires_at = timezone.now() + timedelta(seconds=expires_in)

        defaults = {
            'token_type': token_data.get('token_type', 'bearer'),
            'expires_at': expires_at,
            'is_active': True,
        }

        # Add account info if provided
        if account_info:
            defaults.update(self._extract_account_info(account_info))

        # Get or create auth record
        auth_model = self._get_auth_model()
        self.auth, created = auth_model.objects.update_or_create(
            user=self.user,
            defaults=defaults
        )

        # Set encrypted tokens
        self.auth.decrypted_access_token = token_data['access_token']
        if token_data.get('refresh_token'):
            self.auth.decrypted_refresh_token = token_data['refresh_token']

        # Handle scopes if present
        if 'scope' in token_data:
            scope = token_data['scope']
            self.auth.scopes = scope.split() if isinstance(scope, str) else scope

        self.auth.save()
        
        action = "created" if created else "updated"
        logger.info(f"{self.PROVIDER_NAME} tokens {action} for user {self.user.id}")

    def _extract_account_info(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract account info into model fields. Override in subclasses for provider-specific mapping.
        
        Args:
            account_info: Raw account info from provider
            
        Returns:
            Dict with model field names as keys
        """
        return {
            'account_id': account_info.get('id', ''),
            'email': account_info.get('email', ''),
            'display_name': account_info.get('name', ''),
        }

    def disconnect(self) -> bool:
        """
        Disconnect by deactivating the auth record.
        
        Returns:
            True if successful
        """
        if not self.auth:
            return True

        # Try to revoke token with provider (best effort)
        self._revoke_token()

        # Deactivate locally
        self.auth.is_active = False
        self.auth.save()

        logger.info(f"{self.PROVIDER_NAME} disconnected for user {self.user.id}")
        return True

    def _revoke_token(self) -> None:
        """Revoke token with provider. Override in subclasses if supported."""
        pass

    # =========================================================================
    # API Requests
    # =========================================================================

    def _make_api_request(
        self,
        method: str,
        endpoint: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            base_url: Optional override for base URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
        """
        self._ensure_valid_token()

        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {self.auth.decrypted_access_token}'

        url = f"{base_url or self.API_BASE_URL}/{endpoint.lstrip('/')}" 

        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            error_detail = self._extract_error_detail(e.response)
            logger.error(f"{self.PROVIDER_NAME} API error for user {self.user.id}: {error_detail}")
            raise APIError(
                f"{self.PROVIDER_NAME} API error: {error_detail}",
                status_code=e.response.status_code
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.PROVIDER_NAME} request failed for user {self.user.id}: {e}")
            raise APIError(f"Request failed: {str(e)}")

    def _extract_error_detail(self, response: requests.Response) -> str:
        """Extract error detail from response. Override for provider-specific format."""
        try:
            error_json = response.json()
            return error_json.get('error', {}).get('message', str(error_json))
        except Exception:
            return response.text if response.text else str(response.status_code)

    # =========================================================================
    # Retry Logic
    # =========================================================================

    @staticmethod
    def retry_api_call(
        func: Callable[[], T],
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        retry_on: tuple = (requests.RequestException, ConnectionError, TimeoutError)
    ) -> T:
        """
        Retry an API call with exponential backoff.
        
        Args:
            func: Function to call
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            backoff_factor: Exponential backoff multiplier
            retry_on: Exception types to retry on
            
        Returns:
            Result of the function call
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func()
            except retry_on as e:
                last_exception = e
                if attempt < max_retries:
                    delay = base_delay * (backoff_factor ** attempt)
                    logger.warning(
                        f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"API call failed after {max_retries + 1} attempts: {e}")
                    raise
            except Exception:
                raise

        raise last_exception

    # =========================================================================
    # Abstract Methods for Provider-Specific Operations
    # =========================================================================

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get current user's account information from provider."""
        pass

    @abstractmethod
    def list_folder(self, folder_id: str = None, **kwargs) -> Dict[str, Any]:
        """List contents of a folder."""
        pass

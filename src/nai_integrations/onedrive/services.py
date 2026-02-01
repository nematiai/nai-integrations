"""
OneDrive Integration Services.
"""

import logging
import os
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from django.core.cache import cache
from django.utils import timezone

from nai_integrations.base.exceptions import ConfigurationError, TokenRefreshError
from nai_integrations.base.services import BaseCloudService

from .models import OneDriveAuth

logger = logging.getLogger(__name__)


class OneDriveService(BaseCloudService):
    """Service class for OneDrive API operations."""

    PROVIDER_NAME = "OneDrive"
    API_BASE_URL = "https://graph.microsoft.com/v1.0"
    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    DEFAULT_SCOPES = "offline_access Files.Read Files.Read.All User.Read"

    def _load_auth(self) -> None:
        try:
            self.auth = OneDriveAuth.objects.get(user=self.user, is_active=True)
        except OneDriveAuth.DoesNotExist:
            self.auth = None

    def _get_auth_model(self):
        return OneDriveAuth

    def _get_credentials(self) -> tuple:
        client_id = os.getenv("ONEDRIVE_CLIENT_ID", "")
        client_secret = os.getenv("ONEDRIVE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise ConfigurationError("OneDrive credentials not configured")
        return client_id, client_secret

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        client_id, _ = self._get_credentials()
        if not state:
            state = secrets.token_urlsafe(32)

        cache_key = f"nai_onedrive_state_{self.user.id}_{state}"
        cache.set(cache_key, redirect_uri, timeout=600)

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.DEFAULT_SCOPES,
            "response_mode": "query",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        client_id, client_secret = self._get_credentials()
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        response = requests.post(self.TOKEN_URL, data=data, timeout=10)
        if response.status_code != 200:
            raise TokenRefreshError(f"Token exchange failed: {response.status_code}")
        return response.json()

    def refresh_access_token(self) -> bool:
        if not self.auth or not self.auth.decrypted_refresh_token:
            return False
        client_id, client_secret = self._get_credentials()
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.auth.decrypted_refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        try:
            response = requests.post(self.TOKEN_URL, data=data, timeout=10)
            if response.status_code != 200:
                return False
            token_data = response.json()
            self.auth.decrypted_access_token = token_data["access_token"]
            if token_data.get("refresh_token"):
                self.auth.decrypted_refresh_token = token_data["refresh_token"]
            self.auth.expires_at = timezone.now() + timedelta(
                seconds=token_data.get("expires_in", 3600)
            )
            self.auth.save()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh OneDrive token: {e}")
            return False

    def _extract_account_info(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account_id": account_info.get("id", ""),
            "email": account_info.get("userPrincipalName", "") or account_info.get("mail", ""),
            "display_name": account_info.get("displayName", ""),
        }

    def get_account_info(self) -> Dict[str, Any]:
        response = self._make_api_request("GET", "me")
        return response.json()

    def list_folder(self, folder_id: str = "root", limit: int = 100, **kwargs) -> Dict[str, Any]:
        params = {"$top": min(limit, 200)}
        endpoint = "me/drive/root/children" if folder_id == "root" else f"me/drive/items/{folder_id}/children"
        response = self._make_api_request("GET", endpoint, params=params)
        return response.json()

    def download_file(self, file_id: str) -> bytes:
        response = self._make_api_request("GET", f"me/drive/items/{file_id}/content")
        return response.content

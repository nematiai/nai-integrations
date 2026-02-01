"""
Google Drive Integration Services.
"""

import logging
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from django.utils import timezone

from nai_integrations.base.exceptions import ConfigurationError, TokenRefreshError
from nai_integrations.base.services import BaseCloudService

from .models import GoogleAuth

logger = logging.getLogger(__name__)


class GoogleDriveService(BaseCloudService):
    """Service class for Google Drive API operations."""

    PROVIDER_NAME = "Google Drive"
    API_BASE_URL = "https://www.googleapis.com/drive/v3"
    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"

    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def _load_auth(self) -> None:
        try:
            self.auth = GoogleAuth.objects.get(user=self.user, is_active=True)
        except GoogleAuth.DoesNotExist:
            self.auth = None

    def _get_auth_model(self):
        return GoogleAuth

    def _get_credentials(self) -> tuple:
        client_id = os.getenv("GOOGLE_OAUTH2_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_OAUTH2_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise ConfigurationError("Google OAuth credentials not configured")
        return client_id, client_secret

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> str:
        client_id, _ = self._get_credentials()
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes or self.DEFAULT_SCOPES),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
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
        response = self.retry_api_call(
            lambda: requests.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
        )
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
            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
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
            logger.error(f"Failed to refresh Google token: {e}")
            return False

    def _extract_account_info(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account_id": account_info.get("id", ""),
            "email": account_info.get("email", ""),
            "display_name": account_info.get("name", ""),
            "google_user_id": account_info.get("id", ""),
        }

    def _revoke_token(self) -> None:
        if not self.auth:
            return
        try:
            requests.post(
                self.REVOKE_URL,
                data={"token": self.auth.decrypted_access_token},
                timeout=10,
            )
        except Exception as e:
            logger.warning(f"Failed to revoke Google token: {e}")

    def get_account_info(self) -> Dict[str, Any]:
        self._ensure_valid_token()
        response = self.retry_api_call(
            lambda: requests.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {self.auth.decrypted_access_token}"},
                timeout=10,
            )
        )
        if response.status_code != 200:
            raise TokenRefreshError(f"Failed to get account info: {response.status_code}")
        return response.json()

    def list_folder(
        self,
        folder_id: str = "root",
        page_size: int = 100,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        params = {
            "pageSize": min(page_size, 1000),
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink)",
        }
        q_parts = [f"'{folder_id}' in parents", "trashed=false"]
        if query:
            q_parts.append(query)
        params["q"] = " and ".join(q_parts)
        if page_token:
            params["pageToken"] = page_token
        response = self._make_api_request("GET", "files", params=params)
        return response.json()

    def list_all_files(self, page_size: int = 100, query: Optional[str] = None) -> Dict[str, Any]:
        params = {
            "pageSize": min(page_size, 100),
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink)",
            "q": "trashed=false and 'me' in owners",
        }
        if query:
            params["q"] += f" and {query}"
        response = self._make_api_request("GET", "files", params=params)
        return response.json()

    def download_file(self, file_id: str) -> bytes:
        response = self._make_api_request("GET", f"files/{file_id}", params={"alt": "media"})
        return response.content

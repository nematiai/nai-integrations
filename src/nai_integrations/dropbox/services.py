"""
Dropbox Integration Services.
"""

import logging
import os
from datetime import timedelta
from typing import Any, Dict, Optional

import requests
from django.utils import timezone

from nai_integrations.base.exceptions import ConfigurationError
from nai_integrations.base.services import BaseCloudService

from .models import DropboxAuth

logger = logging.getLogger(__name__)


class DropboxService(BaseCloudService):
    """Service class for Dropbox API operations."""

    PROVIDER_NAME = "Dropbox"
    API_BASE_URL = "https://api.dropboxapi.com/2"
    CONTENT_API_URL = "https://content.dropboxapi.com/2"
    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
    DEFAULT_TOKEN_EXPIRY = 14400

    def _load_auth(self) -> None:
        try:
            self.auth = DropboxAuth.objects.get(user=self.user, is_active=True)
        except DropboxAuth.DoesNotExist:
            self.auth = None

    def _get_auth_model(self):
        return DropboxAuth

    def _get_credentials(self) -> tuple:
        client_id = os.getenv("DROPBOX_CLIENT_ID", os.getenv("DROPBOX_APP_KEY", ""))
        client_secret = os.getenv(
            "DROPBOX_CLIENT_SECRET", os.getenv("DROPBOX_APP_SECRET", "")
        )
        if not client_id or not client_secret:
            raise ConfigurationError("Dropbox credentials not configured")
        return client_id, client_secret

    def get_authorization_url(
        self, redirect_uri: str, state: Optional[str] = None
    ) -> str:
        client_id, _ = self._get_credentials()
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "token_access_type": "offline",
        }
        if state:
            params["state"] = state
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTH_URL}?{query_string}"

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
            lambda: requests.post(self.TOKEN_URL, data=data, timeout=10)
        )
        response.raise_for_status()
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
            response.raise_for_status()
            token_data = response.json()
            self.auth.decrypted_access_token = token_data["access_token"]
            self.auth.expires_at = timezone.now() + timedelta(
                seconds=token_data.get("expires_in", self.DEFAULT_TOKEN_EXPIRY)
            )
            self.auth.save()
            logger.info(f"Dropbox token refreshed for user {self.user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh Dropbox token: {e}")
            return False

    def _extract_account_info(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account_id": account_info.get("account_id", ""),
            "email": account_info.get("email", ""),
            "display_name": account_info.get("name", {}).get("display_name", ""),
        }

    def _revoke_token(self) -> None:
        if not self.auth:
            return
        try:
            self._make_api_request("POST", "auth/token/revoke")
        except Exception as e:
            logger.warning(f"Failed to revoke Dropbox token: {e}")

    def get_account_info(self) -> Dict[str, Any]:
        response = self._make_api_request("POST", "users/get_current_account")
        return response.json()

    def list_folder(self, path: str = "", **kwargs) -> Dict[str, Any]:
        data = {
            "path": path or "",
            "recursive": False,
            "include_media_info": False,
            "include_deleted": False,
        }
        response = self._make_api_request("POST", "files/list_folder", json=data)
        return response.json()

    def list_folder_continue(self, cursor: str) -> Dict[str, Any]:
        data = {"cursor": cursor}
        response = self._make_api_request("POST", "files/list_folder/continue", json=data)
        return response.json()

    def download_file(self, path: str) -> bytes:
        import json

        self._ensure_valid_token()
        headers = {
            "Authorization": f"Bearer {self.auth.decrypted_access_token}",
            "Dropbox-API-Arg": json.dumps({"path": path}),
        }
        response = requests.post(
            f"{self.CONTENT_API_URL}/files/download", headers=headers, timeout=60
        )
        response.raise_for_status()
        return response.content

"""
Box Integration Services.
"""

import logging
import os
from datetime import timedelta
from typing import Any, Dict, Optional

import requests
from django.utils import timezone

from nai_integrations.base.exceptions import ConfigurationError
from nai_integrations.base.services import BaseCloudService

from .models import BoxAuth

logger = logging.getLogger(__name__)


class BoxService(BaseCloudService):
    """Service class for Box API operations."""

    PROVIDER_NAME = "Box"
    API_BASE_URL = "https://api.box.com/2.0"
    AUTH_URL = "https://account.box.com/api/oauth2/authorize"
    TOKEN_URL = "https://api.box.com/oauth2/token"
    UPLOAD_URL = "https://upload.box.com/api/2.0"

    def _load_auth(self) -> None:
        try:
            self.auth = BoxAuth.objects.get(user=self.user, is_active=True)
        except BoxAuth.DoesNotExist:
            self.auth = None

    def _get_auth_model(self):
        return BoxAuth

    def _get_credentials(self) -> tuple:
        client_id = os.getenv("BOX_CLIENT_ID", "")
        client_secret = os.getenv("BOX_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise ConfigurationError("Box credentials not configured")
        return client_id, client_secret

    def get_authorization_url(
        self, redirect_uri: str, state: Optional[str] = None
    ) -> str:
        client_id, _ = self._get_credentials()
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
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
            if token_data.get("refresh_token"):
                self.auth.decrypted_refresh_token = token_data["refresh_token"]
            self.auth.expires_at = timezone.now() + timedelta(
                seconds=token_data.get("expires_in", 3600)
            )
            self.auth.save()
            logger.info(f"Box token refreshed for user {self.user.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh Box token: {e}")
            return False

    def _extract_account_info(self, account_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account_id": account_info.get("id", ""),
            "email": account_info.get("login", ""),
            "display_name": account_info.get("name", ""),
        }

    def _revoke_token(self) -> None:
        if not self.auth:
            return
        try:
            client_id, client_secret = self._get_credentials()
            data = {
                "token": self.auth.decrypted_access_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }
            requests.post(
                "https://api.box.com/oauth2/revoke", data=data, timeout=10
            )
        except Exception as e:
            logger.warning(f"Failed to revoke Box token: {e}")

    def get_account_info(self) -> Dict[str, Any]:
        response = self._make_api_request("GET", "users/me")
        return response.json()

    def list_folder(
        self, folder_id: str = "0", limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        params = {
            "limit": limit,
            "offset": offset,
            "fields": "id,name,type,size,modified_at,path_collection",
        }
        response = self._make_api_request(
            "GET", f"folders/{folder_id}/items", params=params
        )
        return response.json()

    def download_file(self, file_id: str) -> bytes:
        response = self._make_api_request("GET", f"files/{file_id}/content")
        return response.content

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        response = self._make_api_request("GET", f"files/{file_id}")
        return response.json()

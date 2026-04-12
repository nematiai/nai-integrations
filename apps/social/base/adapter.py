"""Abstract base adapter for social media platforms."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseSocialAdapter(ABC):
    """Abstract base for all social media adapters."""

    platform_name: str = ""
    max_content_length: int = 0
    supports_media: bool = False

    def __init__(self, credentials: dict) -> None:
        self.credentials = credentials
        self.validate_credentials()

    @abstractmethod
    def validate_credentials(self) -> None:
        """Raise ConfigurationError if credentials are invalid/missing."""

    @abstractmethod
    def post(
        self,
        content: str,
        media_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post content to the platform.

        Returns:
            {"external_id": "...", "url": "...", "raw": {...}}
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if credentials are valid and API is reachable."""

    def truncate_content(self, content: str) -> str:
        """Truncate content to platform's max length."""
        if self.max_content_length and len(content) > self.max_content_length:
            return content[: self.max_content_length - 3] + "..."
        return content

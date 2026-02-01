"""
Authentication adapter for integrating with different Django authentication systems.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseAuthAdapter(ABC):
    """Abstract base class for authentication adapters."""

    @abstractmethod
    def get_user_from_request(self, request: HttpRequest) -> Optional[User]:
        """Get the authenticated user from a request."""
        pass

    @abstractmethod
    def get_ninja_auth(self) -> Any:
        """Return the django-ninja authentication class/callable."""
        pass

    def require_auth(self, request: HttpRequest) -> User:
        """Require authentication, raising an exception if not authenticated."""
        user = self.get_user_from_request(request)
        if not user:
            from nai_integrations.base.exceptions import AuthenticationError

            raise AuthenticationError("Authentication required")
        return user


class DefaultAuthAdapter(BaseAuthAdapter):
    """Default authentication adapter using Django's session auth."""

    def get_user_from_request(self, request: HttpRequest) -> Optional[User]:
        if hasattr(request, "user") and request.user.is_authenticated:
            return request.user
        return None

    def get_ninja_auth(self) -> Any:
        from ninja.security import django_auth

        return django_auth


def get_auth_adapter() -> BaseAuthAdapter:
    """Get the configured authentication adapter."""
    nai_settings = getattr(settings, "NAI_INTEGRATIONS", {})
    adapter_path = nai_settings.get("AUTH_ADAPTER")

    if not adapter_path:
        return DefaultAuthAdapter()

    try:
        module_path, class_name = adapter_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        adapter_class = getattr(module, class_name)
        return adapter_class()
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load AUTH_ADAPTER '{adapter_path}': {e}")
        raise ImportError(f"Could not load authentication adapter: {adapter_path}")


def require_auth(request: HttpRequest) -> User:
    """Convenience function to require authentication."""
    adapter = get_auth_adapter()
    return adapter.require_auth(request)


def get_ninja_auth():
    """Get the ninja auth class from the configured adapter."""
    adapter = get_auth_adapter()
    return adapter.get_ninja_auth()

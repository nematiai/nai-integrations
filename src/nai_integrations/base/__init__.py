"""
Base classes for cloud storage integrations.
"""


def __getattr__(name):
    """Lazy import to avoid Django AppRegistryNotReady errors."""
    if name == "BaseCloudAuth":
        from .models import BaseCloudAuth
        return BaseCloudAuth
    elif name == "BaseCloudService":
        from .services import BaseCloudService
        return BaseCloudService
    elif name in ("ConnectionStatusOut", "AuthorizeOut", "DisconnectOut", "FileInfo", "ContentsOut"):
        from . import schemas
        return getattr(schemas, name)
    elif name in ("IntegrationError", "AuthenticationError", "TokenRefreshError", "APIError", "ConfigurationError", "RateLimitError"):
        from . import exceptions
        return getattr(exceptions, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseCloudAuth",
    "BaseCloudService",
    "ConnectionStatusOut",
    "AuthorizeOut",
    "DisconnectOut",
    "FileInfo",
    "ContentsOut",
    "IntegrationError",
    "AuthenticationError",
    "TokenRefreshError",
    "APIError",
    "ConfigurationError",
    "RateLimitError",
]

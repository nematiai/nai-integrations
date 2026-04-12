"""Base classes for cloud storage integrations."""


def __getattr__(name: str):
    """Lazy import to avoid Django AppRegistryNotReady errors."""
    _model_names = {"BaseCloudAuth"}
    _service_names = {"BaseCloudService"}
    _schema_names = {
        "ConnectionStatusOut",
        "AuthorizeOut",
        "DisconnectOut",
        "FileInfo",
        "ContentsOut",
    }
    _exception_names = {
        "IntegrationError",
        "AuthenticationError",
        "TokenRefreshError",
        "APIError",
        "ConfigurationError",
        "RateLimitError",
    }

    if name in _model_names:
        from .models import BaseCloudAuth

        return BaseCloudAuth
    if name in _service_names:
        from .services import BaseCloudService

        return BaseCloudService
    if name in _schema_names:
        from . import schemas

        return getattr(schemas, name)
    if name in _exception_names:
        from apps.core.base import exceptions

        return getattr(exceptions, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

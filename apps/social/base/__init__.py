"""Base classes for social media integrations."""


def __getattr__(name: str):
    """Lazy import to avoid Django AppRegistryNotReady errors."""
    _model_names = {"SocialAccount", "PostLog"}
    _adapter_names = {"BaseSocialAdapter"}
    _schema_names = {
        "RegisterAccountIn",
        "AccountOut",
        "PostIn",
        "PostOut",
        "PlatformOut",
        "HealthOut",
    }
    _exception_names = {
        "IntegrationError",
        "AuthenticationError",
        "ConfigurationError",
        "APIError",
        "RateLimitError",
    }

    if name in _model_names:
        from . import models

        return getattr(models, name)
    if name in _adapter_names:
        from .adapter import BaseSocialAdapter

        return BaseSocialAdapter
    if name in _schema_names:
        from . import schemas

        return getattr(schemas, name)
    if name in _exception_names:
        from apps.core.base import exceptions

        return getattr(exceptions, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

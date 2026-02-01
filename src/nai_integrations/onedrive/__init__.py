"""
OneDrive cloud storage integration.
"""


def __getattr__(name):
    if name == "OneDriveAuth":
        from .models import OneDriveAuth
        return OneDriveAuth
    elif name == "OneDriveService":
        from .services import OneDriveService
        return OneDriveService
    elif name == "router":
        from .views import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["OneDriveAuth", "OneDriveService", "router"]

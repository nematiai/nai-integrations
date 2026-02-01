"""
Google Drive cloud storage integration.
"""


def __getattr__(name):
    if name == "GoogleAuth":
        from .models import GoogleAuth
        return GoogleAuth
    elif name == "GoogleDriveService":
        from .services import GoogleDriveService
        return GoogleDriveService
    elif name == "router":
        from .views import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GoogleAuth", "GoogleDriveService", "router"]

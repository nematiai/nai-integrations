"""
Dropbox cloud storage integration.
"""


def __getattr__(name):
    if name == "DropboxAuth":
        from .models import DropboxAuth
        return DropboxAuth
    elif name == "DropboxService":
        from .services import DropboxService
        return DropboxService
    elif name == "router":
        from .views import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DropboxAuth", "DropboxService", "router"]

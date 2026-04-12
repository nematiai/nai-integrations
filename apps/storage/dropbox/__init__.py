"""Dropbox cloud storage integration."""


def __getattr__(name: str):
    if name == "DropboxAuth":
        from .models import DropboxAuth

        return DropboxAuth
    if name == "DropboxService":
        from .services import DropboxService

        return DropboxService
    if name == "router":
        from .views import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DropboxAuth", "DropboxService", "router"]

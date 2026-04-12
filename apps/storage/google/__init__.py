"""Google Drive cloud storage integration."""


def __getattr__(name: str):
    if name == "GoogleAuth":
        from .models import GoogleAuth

        return GoogleAuth
    if name == "GoogleDriveService":
        from .services import GoogleDriveService

        return GoogleDriveService
    if name == "router":
        from .views import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GoogleAuth", "GoogleDriveService", "router"]

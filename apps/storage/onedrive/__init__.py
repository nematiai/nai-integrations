"""OneDrive cloud storage integration."""


def __getattr__(name: str):
    if name == "OneDriveAuth":
        from .models import OneDriveAuth

        return OneDriveAuth
    if name == "OneDriveService":
        from .services import OneDriveService

        return OneDriveService
    if name == "router":
        from .views import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["OneDriveAuth", "OneDriveService", "router"]

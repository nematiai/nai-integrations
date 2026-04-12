"""Box cloud storage integration."""


def __getattr__(name: str):
    if name == "BoxAuth":
        from .models import BoxAuth

        return BoxAuth
    if name == "BoxService":
        from .services import BoxService

        return BoxService
    if name == "router":
        from .views import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["BoxAuth", "BoxService", "router"]

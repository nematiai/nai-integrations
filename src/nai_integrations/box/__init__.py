"""
Box cloud storage integration.
"""


def __getattr__(name):
    if name == "BoxAuth":
        from .models import BoxAuth
        return BoxAuth
    elif name == "BoxService":
        from .services import BoxService
        return BoxService
    elif name == "router":
        from .views import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["BoxAuth", "BoxService", "router"]

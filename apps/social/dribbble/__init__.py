"""Dribbble social adapter."""


def __getattr__(name: str):
    if name == "DribbbleAdapter":
        from apps.social.dribbble.adapter import DribbbleAdapter

        return DribbbleAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

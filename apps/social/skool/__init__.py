"""Skool social adapter."""


def __getattr__(name: str):
    if name == "SkoolAdapter":
        from apps.social.skool.adapter import SkoolAdapter

        return SkoolAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

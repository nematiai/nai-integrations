"""Whop social adapter."""


def __getattr__(name: str):
    if name == "WhopAdapter":
        from apps.social.whop.adapter import WhopAdapter

        return WhopAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

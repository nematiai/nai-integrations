"""X (Twitter) social adapter."""


def __getattr__(name: str):
    if name == "XAdapter":
        from apps.social.x.adapter import XAdapter

        return XAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

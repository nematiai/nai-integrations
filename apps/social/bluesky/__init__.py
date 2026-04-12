"""Bluesky social adapter."""


def __getattr__(name: str):
    if name == "BlueskyAdapter":
        from apps.social.bluesky.adapter import BlueskyAdapter

        return BlueskyAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Instagram social adapter."""


def __getattr__(name: str):
    if name == "InstagramAdapter":
        from apps.social.instagram.adapter import InstagramAdapter

        return InstagramAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

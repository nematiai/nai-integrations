"""YouTube social adapter."""


def __getattr__(name: str):
    if name == "YouTubeAdapter":
        from apps.social.youtube.adapter import YouTubeAdapter

        return YouTubeAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Reddit social adapter."""


def __getattr__(name: str):
    if name == "RedditAdapter":
        from apps.social.reddit.adapter import RedditAdapter

        return RedditAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

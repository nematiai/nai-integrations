"""Facebook social adapter."""


def __getattr__(name: str):
    if name == "FacebookAdapter":
        from apps.social.facebook.adapter import FacebookAdapter

        return FacebookAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

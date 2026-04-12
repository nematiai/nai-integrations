"""MeWe social adapter."""


def __getattr__(name: str):
    if name == "MeWeAdapter":
        from apps.social.mewe.adapter import MeWeAdapter

        return MeWeAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

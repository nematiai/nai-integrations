"""Pinterest social adapter."""


def __getattr__(name: str):
    if name == "PinterestAdapter":
        from apps.social.pinterest.adapter import PinterestAdapter

        return PinterestAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

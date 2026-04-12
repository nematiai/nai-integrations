"""Google Business Profile social adapter."""


def __getattr__(name: str):
    if name == "GoogleBusinessAdapter":
        from apps.social.google_business.adapter import GoogleBusinessAdapter

        return GoogleBusinessAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

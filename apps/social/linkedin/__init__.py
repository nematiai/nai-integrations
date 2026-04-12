"""LinkedIn personal profile social adapter."""


def __getattr__(name: str):
    if name == "LinkedInAdapter":
        from apps.social.linkedin.adapter import LinkedInAdapter

        return LinkedInAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

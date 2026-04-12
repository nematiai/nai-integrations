"""LinkedIn company page social adapter."""


def __getattr__(name: str):
    if name == "LinkedInPageAdapter":
        from apps.social.linkedin_page.adapter import LinkedInPageAdapter

        return LinkedInPageAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

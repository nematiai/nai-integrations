"""Mastodon social adapter."""


def __getattr__(name: str):
    if name == "MastodonAdapter":
        from apps.social.mastodon.adapter import MastodonAdapter

        return MastodonAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

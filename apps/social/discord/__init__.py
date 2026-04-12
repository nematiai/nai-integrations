"""Discord social adapter."""


def __getattr__(name: str):
    if name == "DiscordAdapter":
        from apps.social.discord.adapter import DiscordAdapter

        return DiscordAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

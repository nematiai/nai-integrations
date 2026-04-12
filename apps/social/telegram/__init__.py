"""Telegram social adapter."""


def __getattr__(name: str):
    if name == "TelegramAdapter":
        from apps.social.telegram.adapter import TelegramAdapter

        return TelegramAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

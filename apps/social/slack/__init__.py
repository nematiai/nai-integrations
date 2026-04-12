"""Slack social adapter."""


def __getattr__(name: str):
    if name == "SlackAdapter":
        from apps.social.slack.adapter import SlackAdapter

        return SlackAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

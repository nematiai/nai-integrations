"""Threads social adapter."""


def __getattr__(name: str):
    if name == "ThreadsAdapter":
        from apps.social.threads.adapter import ThreadsAdapter

        return ThreadsAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

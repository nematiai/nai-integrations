"""Social media adapter registry."""

from typing import Dict, Type

from apps.social.base.adapter import BaseSocialAdapter

# Populated by Step 5 when adapters are built
ADAPTERS: Dict[str, Type[BaseSocialAdapter]] = {}


def _register_adapters() -> None:
    """Register all built-in adapters."""
    from apps.social.bluesky.adapter import BlueskyAdapter
    from apps.social.discord.adapter import DiscordAdapter
    from apps.social.dribbble.adapter import DribbbleAdapter
    from apps.social.facebook.adapter import FacebookAdapter
    from apps.social.google_business.adapter import GoogleBusinessAdapter
    from apps.social.instagram.adapter import InstagramAdapter
    from apps.social.linkedin.adapter import LinkedInAdapter
    from apps.social.linkedin_page.adapter import LinkedInPageAdapter
    from apps.social.mastodon.adapter import MastodonAdapter
    from apps.social.mewe.adapter import MeWeAdapter
    from apps.social.pinterest.adapter import PinterestAdapter
    from apps.social.reddit.adapter import RedditAdapter
    from apps.social.skool.adapter import SkoolAdapter
    from apps.social.slack.adapter import SlackAdapter
    from apps.social.telegram.adapter import TelegramAdapter
    from apps.social.threads.adapter import ThreadsAdapter
    from apps.social.tiktok.adapter import TikTokAdapter
    from apps.social.whop.adapter import WhopAdapter
    from apps.social.x.adapter import XAdapter
    from apps.social.youtube.adapter import YouTubeAdapter

    ADAPTERS["telegram"] = TelegramAdapter
    ADAPTERS["discord"] = DiscordAdapter
    ADAPTERS["slack"] = SlackAdapter
    ADAPTERS["reddit"] = RedditAdapter
    ADAPTERS["bluesky"] = BlueskyAdapter
    ADAPTERS["mastodon"] = MastodonAdapter
    ADAPTERS["x"] = XAdapter
    ADAPTERS["linkedin"] = LinkedInAdapter
    ADAPTERS["linkedin_page"] = LinkedInPageAdapter
    ADAPTERS["pinterest"] = PinterestAdapter
    ADAPTERS["facebook"] = FacebookAdapter
    ADAPTERS["instagram"] = InstagramAdapter
    ADAPTERS["threads"] = ThreadsAdapter
    ADAPTERS["youtube"] = YouTubeAdapter
    ADAPTERS["tiktok"] = TikTokAdapter
    ADAPTERS["google_business"] = GoogleBusinessAdapter
    ADAPTERS["dribbble"] = DribbbleAdapter
    ADAPTERS["skool"] = SkoolAdapter
    ADAPTERS["whop"] = WhopAdapter
    ADAPTERS["mewe"] = MeWeAdapter


_register_adapters()


def get_adapter(platform: str) -> Type[BaseSocialAdapter]:
    """Get the adapter class for a given platform."""
    if platform not in ADAPTERS:
        raise ValueError(f"Unknown platform: {platform}")
    return ADAPTERS[platform]


def list_platforms() -> list[str]:
    """Return all registered platform names."""
    return list(ADAPTERS.keys())

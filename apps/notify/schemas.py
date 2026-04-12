"""
Service schemas for notification channels.

Loads 80 services from services.json and provides URL building functions.
"""

import json
import re
from pathlib import Path
from urllib.parse import quote

# Load services from JSON
_SERVICES_FILE = Path(__file__).parent / "json" / "Services.JSON"
try:
    with _SERVICES_FILE.open() as f:
        SERVICE_SCHEMAS = json.load(f)
except FileNotFoundError:
    SERVICE_SCHEMAS = {}


# URL Builder Functions
def _extract_slack_tokens(webhook_url: str) -> str:
    match = re.search(
        r"hooks\.slack\.com/services/([^/]+)/([^/]+)/([^/\s]+)", webhook_url
    )
    return f"{match.group(1)}/{match.group(2)}/{match.group(3)}" if match else ""


def _extract_discord_tokens(webhook_url: str) -> str:
    match = re.search(r"discord\.com/api/webhooks/(\d+)/([^/\s]+)", webhook_url)
    return f"{match.group(1)}/{match.group(2)}" if match else ""


def _extract_guilded_tokens(webhook_url: str) -> str:
    match = re.search(r"media\.guilded\.gg/webhooks/([^/]+)/([^/\s]+)", webhook_url)
    return f"{match.group(1)}/{match.group(2)}" if match else ""


def _extract_gchat_tokens(webhook_url: str) -> str:
    return webhook_url.replace("https://chat.googleapis.com/v1/spaces/", "")


def _extract_feishu_token(webhook_url: str) -> str:
    match = re.search(r"open\.feishu\.cn/open-apis/bot/v2/hook/([^/\s]+)", webhook_url)
    return match.group(1) if match else ""


def _strip_protocol(url: str) -> str:
    return url.replace("https://", "").replace("http://", "")


def _encode_url(url: str) -> str:
    return quote(url, safe="")


URL_BUILDERS = {
    "extract_slack_tokens": _extract_slack_tokens,
    "extract_discord_tokens": _extract_discord_tokens,
    "extract_guilded_tokens": _extract_guilded_tokens,
    "extract_gchat_tokens": _extract_gchat_tokens,
    "extract_feishu_token": _extract_feishu_token,
    "strip_protocol": _strip_protocol,
    "encode_url": _encode_url,
}


def _apply_url_builder(schema: dict, config: dict) -> dict:
    """Apply special URL builder if specified."""
    url_builder = schema.get("url_builder")
    if url_builder and url_builder in URL_BUILDERS:
        builder_func = URL_BUILDERS[url_builder]
        for field in schema["fields"]:
            if field["name"] in ["webhook_url", "url"]:
                transformed = builder_func(config.get(field["name"], ""))
                config = {**config, "tokens": transformed, field["name"]: transformed}
                break
    return config


def _build_url_from_pattern(url_pattern: str, schema: dict, config: dict) -> str:
    """Build URL from pattern by replacing fields."""
    result = url_pattern
    for field in schema["fields"]:
        field_name = field["name"]
        value = config.get(field_name, field.get("default", ""))
        if value is None:
            value = ""
        if "phone" in field_name and isinstance(value, str):
            value = value.replace("+", "")
        if field.get("type") == "password" and value:
            value = quote(str(value), safe="")
        result = result.replace("{" + field_name + "}", str(value))
    return result


def _replace_additional_keys(result: str, schema: dict, config: dict) -> str:
    """Replace additional config keys not in schema fields."""
    for key, value in config.items():
        if key not in [f["name"] for f in schema["fields"]]:
            result = result.replace("{" + key + "}", str(value))
    return result


def build_apprise_url(service_type: str, config: dict) -> str:
    """Build Apprise URL from service type and config."""
    schema = SERVICE_SCHEMAS.get(service_type)
    if not schema:
        return ""

    config = _apply_url_builder(schema, config)
    result = _build_url_from_pattern(schema.get("url_pattern", ""), schema, config)
    result = _replace_additional_keys(result, schema, config)
    result = re.sub(r"/+$", "", result)

    return result


def get_service_choices() -> list[tuple[str, str]]:
    """Return choices for Django model field."""
    return [(key, schema["label"]) for key, schema in SERVICE_SCHEMAS.items()]


def get_service_schema(service_type: str) -> dict | None:
    """Get schema for a specific service type."""
    return SERVICE_SCHEMAS.get(service_type)


def get_all_schemas() -> dict:
    """Return all schemas for frontend consumption."""
    return {
        key: {
            "label": schema["label"],
            "icon": schema.get("icon", "bell"),
            "category": schema.get("category", "other"),
            "description": schema.get("description", ""),
            "fields": schema["fields"],
        }
        for key, schema in SERVICE_SCHEMAS.items()
    }


def get_categories() -> dict:
    """Return services grouped by category."""
    categories = {}
    for key, schema in SERVICE_SCHEMAS.items():
        category = schema.get("category", "other")
        if category not in categories:
            categories[category] = []
        categories[category].append(
            {
                "key": key,
                "label": schema["label"],
                "icon": schema.get("icon", "bell"),
            }
        )
    return categories

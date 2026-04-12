"""Shared mock helpers for Bluesky adapter tests."""

from unittest.mock import MagicMock

VALID_CREDS = {
    "handle": "test.bsky.social",
    "app_password": "xxxx-xxxx-xxxx-xxxx",
}


def mock_session_response() -> MagicMock:
    """Mock a successful createSession response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "accessJwt": "jwt_abc",
        "refreshJwt": "jwt_refresh",
        "did": "did:plc:test123",
        "handle": "test.bsky.social",
    }
    return resp


def mock_record_response(
    uri: str = "at://did:plc:test123/app.bsky.feed.post/3k4abc",
    cid: str = "bafyreiabc",
) -> MagicMock:
    """Mock a successful createRecord response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"uri": uri, "cid": cid}
    return resp


def mock_error_response(
    status_code: int = 400,
    error: str = "InvalidRequest",
    message: str = "Bad request",
) -> MagicMock:
    """Mock an XRPC error response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"error": error, "message": message}
    return resp


def mock_blob_response() -> MagicMock:
    """Mock a successful uploadBlob response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "blob": {
            "$type": "blob",
            "ref": {"$link": "bafkreiblob123"},
            "mimeType": "image/jpeg",
            "size": 12345,
        },
    }
    return resp


def mock_media_download(
    status_code: int = 200,
    content_type: str = "image/jpeg",
) -> MagicMock:
    """Mock downloading media from a URL."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = b"fakeimagebytes"
    resp.headers = {"content-type": content_type}
    return resp

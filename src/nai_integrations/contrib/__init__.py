"""
Contrib modules for extending nai-integrations.
"""

from .auth import BaseAuthAdapter, get_auth_adapter, require_auth, get_ninja_auth

__all__ = ["BaseAuthAdapter", "get_auth_adapter", "require_auth", "get_ninja_auth"]

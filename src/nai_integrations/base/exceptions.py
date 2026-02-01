"""
Custom exceptions for cloud storage integrations.
"""


class IntegrationError(Exception):
    """Base exception for all integration errors."""

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code or "INTEGRATION_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(IntegrationError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(message, code="AUTHENTICATION_ERROR", details=details)


class TokenRefreshError(IntegrationError):
    """Raised when token refresh fails."""

    def __init__(self, message: str = "Token refresh failed", details: dict = None):
        super().__init__(message, code="TOKEN_REFRESH_ERROR", details=details)


class APIError(IntegrationError):
    """Raised when API call fails."""

    def __init__(
        self,
        message: str = "API call failed",
        status_code: int = None,
        details: dict = None,
    ):
        self.status_code = status_code
        super().__init__(message, code="API_ERROR", details=details)


class ConfigurationError(IntegrationError):
    """Raised when configuration is missing or invalid."""

    def __init__(self, message: str = "Configuration error", details: dict = None):
        super().__init__(message, code="CONFIGURATION_ERROR", details=details)


class RateLimitError(IntegrationError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__(message, code="RATE_LIMIT_ERROR", details=details)

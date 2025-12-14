"""Authorization-related exception classes."""

from .base import AutoBangumiError


class AuthorizationError(AutoBangumiError):
    """Base class for authorization-related errors."""

    def __init__(self, message: str = "Authorization failed", **kwargs):
        super().__init__(message, **kwargs)


class LoginRequiredError(AuthorizationError):
    """Raised when user is not logged in but authentication is required."""

    def __init__(self, message: str = "Login required", endpoint: str = "", **kwargs):
        if endpoint:
            kwargs["endpoint"] = endpoint
            message = f"Login required to access: {endpoint}"
        super().__init__(message, **kwargs)


class InvalidCredentialsError(AuthorizationError):
    """Raised when login credentials (username/password) are incorrect."""

    def __init__(
        self,
        message: str = "Invalid username or password",
        **kwargs,
    ):
        super().__init__(message, **kwargs)


class ForbiddenError(AuthorizationError):
    """Raised when IP is banned and receives 403 Forbidden response."""

    def __init__(
        self,
        message: str = "Access forbidden, IP has been banned",
        host: str = "",
        **kwargs,
    ):
        if host:
            kwargs["host"] = host
            message = f"Access forbidden by {host}, IP has been banned"
        super().__init__(message, **kwargs)


class TMDBAPIKeyMissingError(AuthorizationError):
    """Raised when TMDB API key is not provided or invalid."""

    def __init__(
        self,
        message: str = "TMDB API key is missing or invalid",
        use_default: bool = False,
        **kwargs,
    ):
        if use_default:
            message = "TMDB API key is missing, using default key (not recommended for production)"
        super().__init__(message, **kwargs)

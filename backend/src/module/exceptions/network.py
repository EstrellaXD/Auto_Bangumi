"""Network-related exception classes."""

from .base import AutoBangumiError


class NetworkError(AutoBangumiError):
    """Base class for network-related errors."""

    def __init__(
        self,
        message: str = "Network request failed",
        url: str = None,
        status_code: int = None,
        **kwargs,
    ):
        if url:
            kwargs["url"] = url
        if status_code:
            kwargs["status_code"] = status_code
        super().__init__(message, **kwargs)


class APIRequestError(NetworkError):
    """Raised when API request fails."""

    def __init__(
        self,
        message: str = "API request failed",
        api_name: str = None,
        **kwargs,
    ):
        if api_name:
            kwargs["api_name"] = api_name
            message = f"{api_name} API request failed"
        super().__init__(message, **kwargs)

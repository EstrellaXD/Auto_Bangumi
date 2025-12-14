"""
Custom exceptions for Auto_Bangumi application.

This module defines all custom exceptions used throughout the application,
organized in a hierarchical structure for better error handling.
"""

from .auth import (
    AuthorizationError,
    ForbiddenError,
    InvalidCredentialsError,
    LoginRequiredError,
    TMDBAPIKeyMissingError,
)
from .base import AutoBangumiError
from .network import APIRequestError, NetworkError
from .parser import (
    MetaParseError,
    MikanPageParseError,
    ParserError,
    RSSParseError,
    TorrentNameParseError,
    XMLParseError,
)

__all__ = [
    # Base exceptions
    "AutoBangumiError",
    # Authorization errors
    "AuthorizationError",
    "ForbiddenError",
    "InvalidCredentialsError",
    "LoginRequiredError",
    "TMDBAPIKeyMissingError",
    # Parser errors
    "ParserError",
    "XMLParseError",
    "RSSParseError",
    "TorrentNameParseError",
    "MetaParseError",
    "MikanPageParseError",
    # Network errors
    "NetworkError",
    "APIRequestError",
]

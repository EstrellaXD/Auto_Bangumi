"""Module package for Auto_Bangumi."""

from .exceptions import (
    APIRequestError,
    AuthorizationError,
    AutoBangumiError,
    LoginRequiredError,
    MetaParseError,
    NetworkError,
    ParserError,
    RSSParseError,
    TMDBAPIKeyMissingError,
    TorrentNameParseError,
    XMLParseError,
)

__all__ = [
    # Base exceptions
    "AutoBangumiError",
    # Authorization errors
    "AuthorizationError",
    "LoginRequiredError",
    "TMDBAPIKeyMissingError",
    # Parser errors
    "ParserError",
    "XMLParseError",
    "RSSParseError",
    "TorrentNameParseError",
    "MetaParseError",
    # Network errors
    "NetworkError",
    "APIRequestError",
]

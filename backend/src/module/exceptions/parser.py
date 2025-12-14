"""Parsing-related exception classes."""

from .base import AutoBangumiError


class ParserError(AutoBangumiError):
    """Base class for parsing-related errors."""

    def __init__(self, message: str = "Parsing failed", source: str = None, **kwargs):
        if source:
            kwargs["source"] = source
        super().__init__(message, **kwargs)


class XMLParseError(ParserError):
    """Raised when XML parsing fails."""

    def __init__(
        self,
        message: str = "XML parsing failed",
        url: str = "",
        **kwargs,
    ):
        if url:
            kwargs["url"] = url
            message = f"{message}: {url}"
        super().__init__(message, **kwargs)


class RSSParseError(XMLParseError):
    """Raised when RSS feed parsing fails."""

    def __init__(
        self,
        message: str = "RSS feed parsing failed",
        url: str = None,
        **kwargs,
    ):
        super().__init__(message, url=url, **kwargs)


class TorrentNameParseError(ParserError):
    """Raised when torrent name parsing fails."""

    def __init__(
        self,
        message: str = "Torrent name parsing failed",
        torrent_name: str = None,
        **kwargs,
    ):
        if torrent_name:
            kwargs["torrent_name"] = torrent_name
            message = f"{message}: {torrent_name}"
        super().__init__(message, **kwargs)


class MetaParseError(ParserError):
    """Raised when metadata parsing fails."""

    def __init__(
        self,
        message: str = "Metadata parsing failed",
        field: str = None,
        **kwargs,
    ):
        if field:
            kwargs["field"] = field
            message = f"{message} for field: {field}"
        super().__init__(message, **kwargs)


class MikanPageParseError(ParserError):
    """Raised when the page is not a valid Mikan page."""

    def __init__(
        self,
        message: str = "Not a valid Mikan page",
        url: str = None,
        **kwargs,
    ):
        if url:
            kwargs["url"] = url
            message = f"{message}: {url}"
        super().__init__(message, **kwargs)

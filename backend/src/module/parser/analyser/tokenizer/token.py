from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    UNKNOWN = auto()
    GROUP = auto()
    TITLE_ZH = auto()
    TITLE_EN = auto()
    TITLE_JP = auto()
    EPISODE = auto()
    SEASON = auto()
    RESOLUTION = auto()
    SOURCE = auto()
    SUBTITLE = auto()
    CODEC = auto()
    AUDIO = auto()
    CONTAINER = auto()
    PREFIX_TAG = auto()
    VERSION = auto()
    END_MARKER = auto()
    HASH = auto()
    MOVIE = auto()  # movie/gekijouban marker
    EXTRA = auto()


@dataclass(slots=True)
class Token:
    text: str
    kind: TokenKind
    position: int
    enclosed: bool

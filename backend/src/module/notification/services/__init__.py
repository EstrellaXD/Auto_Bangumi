from typing import Literal, TypeAlias

from .bark import BarkService
from .gotify import GotifyService
from .server_chan import ServerChanService
from .slack import SlackService
from .telegram import TelegramService
from .wecom import WecomService

NotificationService: TypeAlias = Literal[
    "bark",
    "telegram",
    "slack",
    "server-chan",
    "wecom",
    "gotify",
]

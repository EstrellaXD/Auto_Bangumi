"""事件基类与宿主发布的通用事件。

事件是冻结 dataclass，``kind`` 为类变量。插件可以定义并发布自己的事件，
``kind`` 须以 ``<plugin-id>.`` 为前缀，避免与宿主事件冲突。
"""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Event:
    kind: ClassVar[str] = "event"


@dataclass(frozen=True, slots=True)
class PluginLoaded(Event):
    kind: ClassVar[str] = "plugin.loaded"
    plugin_id: str
    version: str


@dataclass(frozen=True, slots=True)
class PluginDisabled(Event):
    """插件加载失败，或运行中连续失败被熔断后发布。"""

    kind: ClassVar[str] = "plugin.disabled"
    plugin_id: str
    reason: str

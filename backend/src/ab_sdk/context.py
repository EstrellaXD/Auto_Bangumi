"""插件可见的宿主能力。插件只通过 ``self.ctx`` 访问宿主。"""

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from .events import Event


class KeyValueStore(Protocol):
    """插件私有的持久化键值存储，值须可 JSON 序列化。"""

    async def get(self, key: str, default: Any = None) -> Any: ...

    async def set(self, key: str, value: Any) -> None: ...

    async def delete(self, key: str) -> None: ...


class EventPublisher(Protocol):
    def publish(self, event: Event) -> None: ...

    def subscribe(
        self, kind: str, handler: Callable[[Event], Awaitable[None] | None]
    ) -> Callable[[], None]: ...


class PluginContext(Protocol):
    """只读视图：插件不应替换宿主注入的能力对象。"""

    @property
    def plugin_id(self) -> str: ...

    @property
    def config(self) -> BaseModel | None:
        """已按插件的 config_model 校验；未声明 config_model 时为 None。"""
        ...

    @property
    def log(self) -> logging.Logger: ...

    @property
    def bus(self) -> EventPublisher: ...

    @property
    def kv(self) -> KeyValueStore: ...

    @property
    def data_dir(self) -> Path:
        """config/plugin-data/<id>/，首次访问时创建。"""
        ...

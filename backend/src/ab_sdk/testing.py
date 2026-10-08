"""插件单元测试辅助：不启动 AutoBangumi 也能实例化并驱动插件。

示例::

    from ab_sdk.testing import create_plugin

    async def test_my_filter(tmp_path):
        plugin, ctx = create_plugin(MyPlugin, {"keyword": "1080p"}, data_dir=tmp_path)
        await plugin.setup()
        verdict = await plugin.check(torrent)
        assert verdict.accept
        assert ctx.bus.published == []
"""

import inspect
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .events import Event
from .plugin import Plugin

P = TypeVar("P", bound=Plugin[Any])


class MemoryKV:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)


class RecordingBus:
    """记录插件发布的事件；``deliver`` 把事件同步投递给插件自己的订阅者。"""

    def __init__(self) -> None:
        self.published: list[Event] = []
        self._handlers: list[tuple[str, Callable[[Event], Awaitable[None] | None]]] = []

    def publish(self, event: Event) -> None:
        self.published.append(event)

    def subscribe(
        self, kind: str, handler: Callable[[Event], Awaitable[None] | None]
    ) -> Callable[[], None]:
        entry = (kind, handler)
        self._handlers.append(entry)
        return lambda: self._handlers.remove(entry)

    async def deliver(self, event: Event) -> None:
        for kind, handler in list(self._handlers):
            if kind in ("*", event.kind):
                result = handler(event)
                if inspect.isawaitable(result):
                    await result


class FakeContext:
    def __init__(
        self,
        plugin_id: str,
        config: BaseModel | None,
        data_dir: Path,
    ) -> None:
        self.plugin_id = plugin_id
        self.config = config
        self.log = logging.getLogger(f"plugin.{plugin_id}")
        self.bus = RecordingBus()
        self.kv = MemoryKV()
        self.data_dir = data_dir


def create_plugin(
    plugin_cls: type[P],
    options: dict[str, Any] | None = None,
    *,
    plugin_id: str = "test-plugin",
    data_dir: Path | None = None,
) -> tuple[P, FakeContext]:
    """按宿主的规则校验配置并构造插件（不调用 setup）。"""
    config = None
    if plugin_cls.config_model is not None:
        config = plugin_cls.config_model.model_validate(options or {})
    ctx = FakeContext(plugin_id, config, data_dir or Path("plugin-data") / plugin_id)
    return plugin_cls(ctx), ctx

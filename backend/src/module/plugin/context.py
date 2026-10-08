"""宿主侧的 PluginContext 实现。"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ab_sdk import Event
from ab_sdk.events import SystemEvent

from .bus import EventBus, Handler

PLUGIN_DATA_ROOT = Path("config") / "plugin-data"

# 插件可通知事件的 fire-and-forget 发送任务，保留强引用防止被 GC
_notify_tasks: set[asyncio.Task] = set()


def _database():
    # 延迟 import：module.plugin.host 被网络层、解析器等底层模块引用，
    # 顶层 import module.database 会形成循环依赖
    from module.database import Database

    return Database()


class DatabaseKV:
    """每次读写开一个独立 session，遵守「session per operation」约定。"""

    def __init__(self, plugin_id: str) -> None:
        self._plugin_id = plugin_id

    async def get(self, key: str, default: Any = None) -> Any:
        async with _database() as db:
            found, value = await db.plugin_kv.get(self._plugin_id, key)
        return value if found else default

    async def set(self, key: str, value: Any) -> None:
        async with _database() as db:
            await db.plugin_kv.set(self._plugin_id, key, value)

    async def delete(self, key: str) -> None:
        async with _database() as db:
            await db.plugin_kv.delete(self._plugin_id, key)


class PluginBus:
    """插件视角的总线：订阅归属到插件（卸载时统一清理、失败计入熔断），
    发布的事件 kind 必须以 ``<plugin-id>.`` 开头，防止冒充宿主事件。

    插件发布的 :class:`SystemEvent` 与宿主事件走同一条通知路径
    （``NotificationManager.send_event``：通知中心 → 事件总线 → 外部渠道）。
    """

    def __init__(self, bus: EventBus, plugin_id: str) -> None:
        self._bus = bus
        self._plugin_id = plugin_id

    def publish(self, event: Event) -> None:
        if not event.kind.startswith(f"{self._plugin_id}."):
            raise ValueError(
                f"插件 {self._plugin_id} 只能发布以 '{self._plugin_id}.' 开头的事件，"
                f"收到 {event.kind!r}"
            )
        if isinstance(event, SystemEvent):
            # 延迟 import：notification 依赖 module.plugin.host
            from module.notification import NotificationManager

            task = asyncio.create_task(NotificationManager().send_event(event))
            _notify_tasks.add(task)
            task.add_done_callback(_notify_tasks.discard)
            return
        self._bus.publish(event)

    def subscribe(self, kind: str, handler: Handler):
        return self._bus.subscribe(kind, handler, owner=self._plugin_id)


class HostPluginContext:
    def __init__(
        self,
        plugin_id: str,
        config: BaseModel | None,
        bus: EventBus,
        data_root: Path = PLUGIN_DATA_ROOT,
    ) -> None:
        self.plugin_id = plugin_id
        self.config = config
        self.log = logging.getLogger(f"plugin.{plugin_id}")
        self.bus = PluginBus(bus, plugin_id)
        self.kv = DatabaseKV(plugin_id)
        self._data_dir = data_root / plugin_id

    @property
    def data_dir(self) -> Path:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        return self._data_dir

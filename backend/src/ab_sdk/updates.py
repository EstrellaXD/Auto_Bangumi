"""用户在宿主设置中选定的本地来源；自动检查，安装须由用户操作触发。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PluginUpdateInfo:
    plugin_id: str
    repository: str
    installed_version: str
    version: str
    available: bool
    release_url: str
    notes: str
    install_token: str


class PluginUpdates(Protocol):
    async def check(self) -> PluginUpdateInfo: ...

    async def install(self, version: str, *, install_token: str) -> None: ...

    async def recover(self, operation_id: str) -> None:
        """恢复中断更新的旧代码及插件私有数据；不会回滚媒体文件。"""
        ...

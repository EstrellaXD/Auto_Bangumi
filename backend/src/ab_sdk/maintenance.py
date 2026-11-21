"""维护期间协调宿主任务、备份和进度；跨数据库步骤不承诺共享事务。"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class MaintenanceStatus:
    id: str
    name: str
    state: str
    step: str
    backup_path: str
    error: str


class MaintenanceProgress(Protocol):
    async def checkpoint(self, step: str, details: dict | None = None) -> None: ...


@dataclass(frozen=True, slots=True)
class HistoryPreview:
    token: str
    bangumi_id: int
    # 精确种子行和标题；不把标题猜测为已经确认的集号。
    releases: tuple[tuple[int, str], ...]
    revision: str


@dataclass(frozen=True, slots=True)
class LegacyOutput:
    path: str
    source_identity: tuple[int, ...]
    target_identity: tuple[int, ...]
    naming_strategy: str


class MaintenanceService(Protocol):
    async def operations(self) -> tuple[MaintenanceStatus, ...]: ...

    async def run(
        self, name: str, operation: Callable[[MaintenanceProgress], Awaitable[Any]]
    ) -> Any: ...

    async def status(self, operation_id: str) -> MaintenanceStatus: ...

    async def resume(self, operation_id: str) -> None:
        """用户确认恢复后解除失败维护的阻断；不会暗示媒体或数据已经回滚。"""
        ...

    async def preview_history(
        self, bangumi_id: int, release_ids: tuple[int, ...]
    ) -> HistoryPreview: ...

    async def clear_history(self, token: str) -> None: ...

    async def legacy_outputs(
        self, source_identity: tuple[int, ...], *, work_scope: str
    ) -> tuple[LegacyOutput, ...]: ...

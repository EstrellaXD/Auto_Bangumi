"""供消费下载结果的插件使用；不包含下载器凭据或原始客户端。"""

from dataclasses import dataclass
from typing import Literal, Protocol

from .admission import CandidatePage, Submission, SubmissionPage, SubmitRequest


@dataclass(frozen=True, slots=True)
class DownloadTask:
    download_id: str
    downloader_id: str
    provider_task_id: str
    bangumi_id: int | None
    release_ids: tuple[int, ...]
    association: Literal["matched", "unmatched", "ambiguous"]
    name: str
    save_path: str
    state: str
    progress: float
    revision: int
    observed_at: str


@dataclass(frozen=True, slots=True)
class TaskPage:
    items: tuple[DownloadTask, ...]
    cursor: str | None


@dataclass(frozen=True, slots=True)
class DownloadFile:
    file_id: str
    index: int
    relative_path: str
    original_relative_path: str
    downloader_path: str
    size: int
    selected: bool
    progress: float


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    download_id: str
    revision: int
    files: tuple[DownloadFile, ...]
    observed_at: str


@dataclass(frozen=True, slots=True)
class RefreshResult:
    observed: int
    # 实例 id，不包含主机地址、异常正文或凭据。失败实例保留旧快照。
    unavailable: tuple[str, ...] = ()
    download_ids: tuple[str, ...] = ()


class DownloadService(Protocol):
    async def policy_revision(self) -> str: ...

    async def submit(
        self, request: SubmitRequest, *, idempotency_key: str, policy_revision: str
    ) -> Submission: ...

    async def lookup_submission(self, idempotency_key: str) -> Submission | None: ...

    async def submissions(
        self,
        *,
        bangumi_id: int | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> SubmissionPage:
        """共享只读意图列表；lookup_submission 的幂等键仍按插件隔离。"""
        ...

    async def candidates(
        self,
        *,
        bangumi_id: int | None = None,
        batch_id: str | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> CandidatePage: ...

    async def recheck_candidates(
        self, *, bangumi_id: int | None = None, batch_id: str | None = None
    ) -> int: ...

    async def replay(
        self,
        candidate_id: str,
        *,
        candidate_revision: str,
        mapping_revision: str,
        idempotency_key: str,
        policy_revision: str,
    ) -> Submission: ...

    async def refresh(self) -> RefreshResult:
        """从下载器拉取任务与各文件完成度；失败不得伪装成空任务列表。"""
        ...

    async def list_tasks(
        self,
        *,
        bangumi_id: int | None = None,
        completed: bool | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> TaskPage:
        """查询持久快照。按条目查询只返回唯一归属该条目的任务。"""
        ...

    async def files(self, download_id: str) -> FileSnapshot: ...

    async def associate(
        self, download_id: str, bangumi_id: int, *, revision: int
    ) -> DownloadTask:
        """人工绑定未关联任务；不能覆盖已有归属或过期快照。"""
        ...

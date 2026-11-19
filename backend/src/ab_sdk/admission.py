"""强制下载准入。选中后插件不可用会 hold，不回退到放行。"""

from dataclasses import dataclass
from typing import Literal, Protocol

from .bangumi import BangumiSnapshot
from .ingest import TorrentInfo


@dataclass(frozen=True, slots=True)
class ReleaseSnapshot:
    season: int | None = None
    episode: int | float | None = None
    episode_end: int | float | None = None
    version: int | None = None
    group: str | None = None
    resolution: str | None = None
    subtitle: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    batch_id: str
    source: str
    torrent: TorrentInfo
    bangumi_id: int | None
    stage: str
    reason: str
    revision: str
    matched_bangumi_ids: tuple[int, ...] = ()
    release: ReleaseSnapshot | None = None


@dataclass(frozen=True, slots=True)
class CandidatePage:
    items: tuple[Candidate, ...]
    cursor: str | None


@dataclass(frozen=True, slots=True)
class AdmissionRequest:
    submission_id: str
    candidates: tuple[Candidate, ...]
    bangumi: BangumiSnapshot
    downloader_id: str
    policy_revision: str


@dataclass(frozen=True, slots=True)
class Admission:
    decision: Literal["allow", "hold", "reject"]
    reason: str = ""


class DownloadPreflight(Protocol):
    async def preflight(self, request: AdmissionRequest) -> Admission: ...


@dataclass(frozen=True, slots=True)
class SubmitRequest:
    bangumi_id: int
    torrents: tuple[TorrentInfo, ...]
    mapping_revision: str
    downloader_id: str | None = None
    source: str = "plugin"


@dataclass(frozen=True, slots=True)
class Submission:
    id: str
    idempotency_key: str
    policy_revision: str
    state: Literal["pending", "held", "accepted", "rejected", "unknown", "failed"]
    download_ids: tuple[str, ...]
    reason: str = ""
    bangumi_id: int | None = None
    owner: str = ""


@dataclass(frozen=True, slots=True)
class SubmissionPage:
    items: tuple[Submission, ...]
    cursor: str | None

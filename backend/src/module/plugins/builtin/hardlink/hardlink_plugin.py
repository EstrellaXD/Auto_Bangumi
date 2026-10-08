"""内置插件：硬链接到媒体库（订阅 ``torrent.organized``）。

种子整理完成后，把它的正片与字幕链接到 ``library_root``，相对路径与它们在
``source_root`` 下的相对路径相同。下载目录保持原样继续做种；删除种子时不会
删除媒体库中的链接。

- 事件里的路径是下载器视角，先按 ``path_map`` 换成 AB 本地路径；
- 跨文件系统（EXDEV）时按 ``cross_device`` 复制、建软链接或跳过；
- 目标已存在且不是本插件创建的：跳过并通知；是本插件之前为同一集创建的
  （版本升级后同名文件换成了新文件）：原子替换；
- 事件投递为「至少一次」，已链接的文件再次收到时不做任何事；插件放置后被
  用户从媒体库删除的文件也不重建，只有补链会重建。
"""

import asyncio
import errno
import os
import secrets
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ab_sdk import Plugin, points, provider, subscribe
from ab_sdk.events import Event, SystemEvent, TorrentOrganized

Status = Literal["linked", "exists", "conflict", "failed"]

# 单个种子的处理超时：跨盘复制整季可能需要几分钟
LINK_TIMEOUT = 3600.0

# ponytail: 补链按扩展名挑文件，与宿主 media_files 的 core 实现同一组；插件不能
# import module.*，若用户换了 media_files 实现（P2.5 slots），这里需要改为经 SDK 查询
BACKFILL_SUFFIXES = frozenset({".mp4", ".mkv", ".ass", ".srt"})


class PathMap(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    downloader: str = Field("default", title="下载器", description="下载器实例 id")
    from_: str = Field(
        alias="from", title="下载器路径", description="下载器看到的路径前缀"
    )
    to: str = Field(title="本地路径", description="同一位置在 AutoBangumi 中的路径")


class Options(BaseModel):
    path_map: list[PathMap] = Field(
        default_factory=list,
        title="路径映射",
        description=(
            "下载器与 AutoBangumi 不在同一个文件系统视图（如分别运行在不同容器）"
            "时，把下载器路径前缀换成本地路径；按最长前缀匹配，未匹配的路径原样使用"
        ),
    )
    source_root: str = Field(
        title="下载根目录", description="本地路径，媒体库保持与它相同的目录结构"
    )
    library_root: str = Field(
        title="媒体库目录",
        description="链接放在这里；硬链接要求与下载根目录在同一个文件系统",
    )
    cross_device: Literal["copy", "symlink", "skip"] = Field(
        "copy",
        title="跨文件系统时",
        description="copy 复制文件，symlink 创建软链接，skip 跳过并通知",
    )

    @field_validator("source_root", "library_root")
    @classmethod
    def _absolute(cls, value: str) -> str:
        if not os.path.isabs(value):
            raise ValueError("须为绝对路径")
        return os.path.normpath(value)

    @model_validator(mode="after")
    def _library_outside_source(self) -> "Options":
        # 媒体库在下载目录内时，补链会把媒体库自己再链接一遍
        if Path(self.library_root).is_relative_to(self.source_root):
            raise ValueError("媒体库目录不能位于下载根目录内")
        return self


@dataclass(frozen=True, slots=True)
class HardlinkFailed(SystemEvent):
    """种子中有文件没能链接到媒体库（目标被占用、跨文件系统被跳过等）。"""

    kind: ClassVar[str] = "hardlink.failed"
    severity: ClassVar[str] = "warning"

    torrent_hash: str
    files: str  # 每行一个：路径：原因

    def dedup_key(self) -> str | None:
        return f"hardlink.failed:{self.torrent_hash}"

    def describe(self) -> tuple[str, str]:
        return ("硬链接未完成", f"种子：{self.torrent_hash}\n{self.files}")


@dataclass(frozen=True, slots=True)
class HardlinkLinked(Event):
    """种子有文件新放入了媒体库。跨盘复制可能比媒体库刷新的延迟更久，
    media-server-refresh 订阅它，在文件放好后再刷新一次。"""

    kind: ClassVar[str] = "hardlink.linked"

    torrent_hash: str


def _identity(path: Path) -> list[int]:
    """文件身份（不跟随软链接）。含大小与修改时间：旧文件删除后 inode 可能被复用。"""
    st = os.lstat(path)
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]


def _same(src: Path, dst: Path) -> bool:
    """dst 是 src 的硬链接、软链接，或 copy2 的副本（大小与修改时间相同）。"""
    try:
        if os.path.samefile(src, dst):
            return True
    except OSError:  # 断开的软链接
        return False
    s, d = os.stat(src), os.lstat(dst)
    return stat.S_ISREG(d.st_mode) and (s.st_size, s.st_mtime_ns) == (
        d.st_size,
        d.st_mtime_ns,
    )


def _make(src: Path, dst: Path, cross_device: str) -> tuple[Status, str]:
    """先在同目录的临时文件上建立链接或副本，再原子地移到 ``dst``：复制中断
    （磁盘满、插件重载、进程退出）不会在目标位置留下半个文件，版本升级时也
    不会出现目标暂时缺失的窗口。临时文件名每次不同：补链与订阅可能同时处理
    同一个目标。"""
    tmp = dst.with_name(f".{dst.name}.{secrets.token_hex(4)}.ab-hardlink")
    try:
        try:
            os.link(src, tmp)
        except OSError as e:
            if e.errno != errno.EXDEV:
                raise
            if cross_device == "skip":
                return "failed", "与媒体库不在同一文件系统，已跳过"
            if cross_device == "symlink":
                os.symlink(src, tmp)
            else:
                shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return "linked", ""


# 插件放置的文件：[源文件身份, 目标身份]
Record = list[list[int]]


def place(
    src: Path, dst: Path, owned: Record | None, cross_device: str, restore: bool
) -> tuple[Status, str, Record | None]:
    """在线程中执行的文件操作。``owned`` 是插件上次在 ``dst`` 放置文件时的记录，
    None 表示 ``dst`` 不是插件创建的。``restore`` 为 False 时，插件放置过、之后
    被删除的同一文件不再重建。返回 linked / exists 时附带新记录。"""
    ident = _identity(src)
    if os.path.lexists(dst):
        here = _identity(dst)
        # 指向源文件或是它的副本：即使记录没来得及写入（协程被取消、进程退出）
        # 也认作本插件放置的，并补上记录
        if _same(src, dst) or owned == [ident, here]:
            return "exists", "", [ident, here]
        # 目标被换成了别的文件（用户放的），不能覆盖
        if owned is None or owned[1] != here:
            return "conflict", "媒体库中已有同名文件且不是本插件创建的", None
        # 否则是版本升级：同一集换成了新文件，替换插件之前创建的链接
    elif owned is not None and owned[0] == ident and not restore:
        # 插件放置过同一文件、之后被删除（用户清理已看完的剧集）：重复投递的
        # 事件不再放回，只有用户主动补链时才重建
        return "exists", "", owned
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
    status, reason = _make(src, dst, cross_device)
    return status, reason, [ident, _identity(dst)] if status == "linked" else None


class HardlinkPlugin(Plugin[Options]):
    config_model = Options

    def to_local(self, path: str, downloader: str) -> str:
        best: tuple[str, str] | None = None
        for m in self.config.path_map:
            prefix = m.from_.rstrip("/")
            if m.downloader != downloader:
                continue
            if path != prefix and not path.startswith(f"{prefix}/"):
                continue
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, m.to.rstrip("/"))
        if best is None:
            return path
        return best[1] + path[len(best[0]) :]

    async def link(self, src: Path, restore: bool = False) -> tuple[Status, str]:
        try:
            rel = Path(os.path.normpath(src)).relative_to(self.config.source_root)
        except ValueError:
            return "failed", f"不在下载根目录 {self.config.source_root} 下"
        dst = Path(self.config.library_root) / rel
        key = f"link:{dst}"
        owned = await self.ctx.kv.get(key)
        try:
            status, reason, record = await asyncio.to_thread(
                place, src, dst, owned, self.config.cross_device, restore
            )
        except OSError as e:
            return "failed", str(e)
        if record is not None and record != owned:
            await self.ctx.kv.set(key, record)
        return status, reason

    @subscribe(TorrentOrganized.kind, timeout=LINK_TIMEOUT)
    async def on_organized(self, event: TorrentOrganized) -> None:
        problems: list[str] = []
        linked = False
        for f in event.files:
            status, reason = await self.link(
                Path(self.to_local(f.path, event.downloader_id))
            )
            linked = linked or status == "linked"
            if status in ("conflict", "failed"):
                problems.append(f"{f.path}：{reason}")
        if linked:
            self.ctx.bus.publish(HardlinkLinked(torrent_hash=event.torrent_hash))
        if problems:
            self.ctx.log.warning("种子 %s 未完成链接：%s", event.torrent_hash, problems)
            self.ctx.bus.publish(
                HardlinkFailed(
                    torrent_hash=event.torrent_hash, files="\n".join(problems)
                )
            )

    async def backfill(self) -> dict[Status, int]:
        """把下载根目录下已有的正片与字幕补链到媒体库（只在用户触发时运行）。"""
        root = Path(self.config.source_root)
        files = await asyncio.to_thread(
            lambda: sorted(
                p
                for p in root.rglob("*")
                if p.is_file() and p.suffix.lower() in BACKFILL_SUFFIXES
            )
        )
        counts: dict[Status, int] = {
            "linked": 0,
            "exists": 0,
            "conflict": 0,
            "failed": 0,
        }
        for src in files:
            status, _ = await self.link(src, restore=True)
            counts[status] += 1
        self.ctx.log.info("补链完成：%s", counts)
        return counts

    @provider(points.API_ROUTER, id="api")
    def api(self) -> APIRouter:
        router = APIRouter()

        @router.post("/backfill")
        async def backfill() -> dict[Status, int]:
            return await self.backfill()

        return router

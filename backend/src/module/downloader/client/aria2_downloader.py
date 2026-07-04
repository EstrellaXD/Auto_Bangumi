import asyncio
import hashlib
import logging
import os
import shutil
from typing import ClassVar

import httpx

from module.database import Database
from module.downloader.base import AddResult, DownloaderCapabilities

logger = logging.getLogger(__name__)

# 每次 JSON-RPC 调用的默认超时（秒），auth() 期间的探测调用会传入更短的值。
_DEFAULT_CALL_TIMEOUT = 10.0

# qBittorrent 风格 status_filter -> aria2 status 集合的映射。None（不过滤）
# 之外的未知取值一律当作"不过滤"处理，而不是返回空列表。
_STATUS_FILTER_MAP: dict[str, set[str]] = {
    "completed": {"complete"},
    "downloading": {"active"},
    "active": {"active"},
    "paused": {"paused"},
    "errored": {"error"},
}


class Aria2RpcError(Exception):
    """aria2 JSON-RPC 返回的业务错误（服务器收到了请求，但拒绝执行）。"""

    def __init__(self, code: int | None, message: str):
        self.code = code
        self.message = message
        super().__init__(f"aria2 RPC error {code}: {message}")


class Aria2ConnectionError(Exception):
    """请求根本没有得到 aria2 服务器的有效响应（网络/超时/JSON 解析失败）。"""


class Aria2Downloader:
    # aria2 通过 JSON-RPC 暴露真实的查询/重命名/管理能力（tellActive/tellFiles/
    # changeOption 等），只是没有 qBittorrent 原生的 RSS 规则功能，因此
    # can_rss_rules 保持 False，其余按真实支持情况置 True。
    capabilities: ClassVar[DownloaderCapabilities] = DownloaderCapabilities(
        can_query=True,
        can_rename=True,
        can_manage=True,
        can_rss_rules=False,
    )

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.secret = password
        self._client: httpx.AsyncClient | None = None
        self._authed = False
        self._rpc_url = f"{host}/jsonrpc"
        self._id = 0

    async def _call(
        self,
        method: str,
        params: list | None = None,
        timeout: float = _DEFAULT_CALL_TIMEOUT,
    ):
        assert self._client is not None, "Aria2Downloader.auth() must run first"
        self._id += 1
        full_params = [f"token:{self.secret}"] + (params or [])
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": f"aria2.{method}",
            "params": full_params,
        }
        try:
            resp = await self._client.post(self._rpc_url, json=payload, timeout=timeout)
        except httpx.TimeoutException as e:
            raise Aria2ConnectionError(f"aria2 RPC '{method}' timed out: {e}") from e
        except httpx.RequestError as e:
            raise Aria2ConnectionError(
                f"aria2 RPC '{method}' request failed: {e}"
            ) from e
        try:
            result = resp.json()
        except ValueError as e:
            raise Aria2ConnectionError(
                f"aria2 RPC '{method}' returned invalid JSON: {e}"
            ) from e
        if "error" in result:
            err = result["error"] or {}
            raise Aria2RpcError(err.get("code"), err.get("message", str(err)))
        return result.get("result")

    async def auth(self, retry: int = 3) -> bool:
        if self._client is not None and self._authed:
            return True
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=3.1, read=10.0, write=10.0, pool=10.0)
            )
        times = 0
        while times < retry:
            try:
                await self._call("getVersion")
                self._authed = True
                return True
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning(
                    f"Can't login Aria2 Server {self.host}, retry in 5 seconds. Error: {e}"
                )
                await asyncio.sleep(5)
                times += 1
        return False

    async def logout(self) -> None:
        self._authed = False
        if self._client:
            await self._client.aclose()
            self._client = None

    async def check_connection(self) -> str:
        version = await self._call("getVersion")
        return (version or {}).get("version", "unknown")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_hashes(hashes: str | list[str] | tuple[str, ...]) -> list[str]:
        if isinstance(hashes, (list, tuple)):
            return list(hashes)
        return hashes.split("|") if "|" in hashes else [hashes]

    @staticmethod
    def _parse_bangumi_id_from_tag(tags: str | None) -> int | None:
        """从 'ab:<id>' 格式的 tag/tags 中解出 bangumi_id（与 Renamer 的约定一致）。"""
        if not tags:
            return None
        for tag in tags.split(","):
            tag = tag.strip()
            if tag.startswith("ab:"):
                try:
                    return int(tag[3:])
                except ValueError:
                    pass
        return None

    @staticmethod
    def _is_duplicate_error(e: Aria2RpcError) -> bool:
        msg = e.message.lower()
        return "already" in msg or "duplicate" in msg

    @staticmethod
    def _is_not_found_error(e: Aria2RpcError) -> bool:
        msg = e.message.lower()
        return "not found" in msg or "is not found" in msg

    @staticmethod
    def _extract_name(download: dict) -> str:
        bt_info = (download.get("bittorrent") or {}).get("info") or {}
        if bt_info.get("name"):
            return bt_info["name"]
        files = download.get("files") or []
        if files and files[0].get("path"):
            return os.path.basename(files[0]["path"])
        return download.get("gid", "")

    @staticmethod
    def _extract_followed_by_gid(status: dict | None) -> str | None:
        if not isinstance(status, dict):
            return None
        followed_by = (status or {}).get("followedBy") or []
        if isinstance(followed_by, list) and followed_by:
            return str(followed_by[0])
        return None

    @staticmethod
    def _translate_renamed_path(path: str, renamed_paths: dict[str, str]) -> str:
        seen = set()
        while path in renamed_paths and path not in seen:
            seen.add(path)
            path = renamed_paths[path]
        return path

    @staticmethod
    def _move_file(old_abs: str, new_abs: str) -> None:
        """移动单个文件；目标已存在且不是同一个文件时拒绝覆盖。

        多文件种子若映射到同一目标名，直接覆盖会毁掉已重命名好的文件，
        所以这里显式拦下来。
        """
        if (
            os.path.exists(old_abs)
            and os.path.exists(new_abs)
            and os.path.samefile(old_abs, new_abs)
        ):
            return
        if os.path.exists(new_abs) and not (
            os.path.exists(old_abs) and os.path.samefile(old_abs, new_abs)
        ):
            raise FileExistsError(f"destination already exists: {new_abs}")
        os.makedirs(os.path.dirname(new_abs), exist_ok=True)
        shutil.move(old_abs, new_abs)

    @staticmethod
    def _move_files(files: list[dict], old_dir: str, new_dir: str) -> None:
        old_dir = os.path.normpath(old_dir)
        for f in files:
            path = f.get("path")
            if not path or not os.path.exists(path):
                continue
            rel = os.path.relpath(path, old_dir)
            dest = os.path.join(new_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(path, dest)

    @staticmethod
    def _remove_file_and_empty_dirs(path: str, boundary: str) -> None:
        """删除单个文件，并向上清理变空的父目录，直到 boundary（含）为止不再删除。

        boundary 通常是 aria2 的 ``dir``（bangumi 的 season 目录），可能被多个
        gid 共享，所以绝不删除 boundary 本身或它之外的目录。
        """
        if os.path.exists(path):
            os.remove(path)
        boundary = os.path.normpath(boundary)
        parent = os.path.dirname(path)
        while os.path.normpath(parent) != boundary and (
            os.path.normpath(parent).startswith(boundary + os.sep)
        ):
            try:
                os.rmdir(parent)
            except OSError:
                break
            parent = os.path.dirname(parent)

    # ------------------------------------------------------------------
    # Adding
    # ------------------------------------------------------------------

    async def _dedup_record_is_stale(self, db: Database, gid: str) -> bool | None:
        """dedup 命中后校验 gid 是否仍存在于 aria2；陈旧则删记录并返回 True。

        本地 aria2_gid 表可能和 aria2 真实状态脱节（用户在 aria2 UI 里删了
        任务、或 aria2 没开 --save-session 就重启了），不校验的话陈旧记录
        会让同一个种子永远被当作"已添加"而无法重新下载。

        - RPC 报 not found、或 status 为 "removed" → 记录陈旧，删掉，返回 True；
        - aria2 不可达（连接错误）→ 无法断言，保守保留记录，返回 None；
        - 其余 RPC 错误 → 同样保守保留，返回 None。
        """
        try:
            status = await self._call("tellStatus", [gid, ["status"]])
        except Aria2RpcError as e:
            if self._is_not_found_error(e):
                logger.info(
                    "Stale dedup record: gid %s no longer exists, "
                    "removing and re-adding",
                    gid,
                )
                await db.aria2.delete(gid)
                return True
            logger.debug("Cannot verify gid %s, keeping record: %s", gid, e)
            return None
        except Aria2ConnectionError as e:
            # aria2 不可达 != 记录陈旧，绝不能因此删本地记录。
            logger.debug(
                "aria2 unreachable while verifying gid %s, keeping record: %s",
                gid,
                e,
            )
            return None
        if (status or {}).get("status") == "removed":
            logger.info(
                "Stale dedup record: gid %s was removed in aria2, "
                "removing and re-adding",
                gid,
            )
            await db.aria2.delete(gid)
            return True
        return False

    async def _add_uri(self, url: str, options: dict) -> tuple[AddResult, str | None]:
        try:
            return AddResult.ADDED, await self._call("addUri", [[url], options])
        except Aria2RpcError as e:
            if self._is_duplicate_error(e):
                logger.debug("addUri reports duplicate: %s", e.message)
                return AddResult.DUPLICATE, None
            else:
                logger.error("addUri failed for %s: %s", url, e)
                return AddResult.FAILED, None
        except Aria2ConnectionError as e:
            logger.error("addUri connection error for %s: %s", url, e)
            return AddResult.FAILED, None

    async def _add_torrent_file(
        self, data: bytes, options: dict
    ) -> tuple[AddResult, str | None]:
        import base64

        b64 = base64.b64encode(data).decode()
        try:
            return AddResult.ADDED, await self._call("addTorrent", [b64, [], options])
        except Aria2RpcError as e:
            if self._is_duplicate_error(e):
                logger.debug("addTorrent reports duplicate: %s", e.message)
                return AddResult.DUPLICATE, None
            else:
                logger.error("addTorrent failed: %s", e)
                return AddResult.FAILED, None
        except Aria2ConnectionError as e:
            logger.error("addTorrent connection error: %s", e)
            return AddResult.FAILED, None

    async def _resolve_followed_by_gid(self, gid: str) -> str:
        try:
            status = await self._call("tellStatus", [gid, ["followedBy"]])
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.debug("Could not resolve followedBy for %s: %s", gid, e)
            return gid
        return self._extract_followed_by_gid(status) or gid

    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ) -> AddResult:
        """添加下载任务，返回新增/重复/失败的三态结果。

        去重优先靠本地的 dedup_key（url 或种子内容 hash）判断"已经添加过"，
        aria2 RPC 报错里带 already/duplicate 字样时也当作重复处理（见
        ``_is_duplicate_error``）——这样调用方（DownloadClient.add_torrent）
        才能像 qBittorrent 一样区分"新增成功"和"之前加过了"。
        """
        bangumi_id = self._parse_bangumi_id_from_tag(tags)
        options = {"dir": save_path}
        added_any = False
        duplicate_any = False
        failed_any = False
        async with Database() as db:
            if torrent_urls:
                urls = (
                    torrent_urls if isinstance(torrent_urls, list) else [torrent_urls]
                )
                for url in urls:
                    dedup_key = f"url:{url}"
                    existing_gid = await db.aria2.find_by_dedup_key(dedup_key)
                    if existing_gid:
                        stale = await self._dedup_record_is_stale(db, existing_gid)
                        if stale is None:
                            failed_any = True
                            continue
                        if not stale:
                            logger.debug("Skip already-added url: %s", url)
                            duplicate_any = True
                            continue
                    result, gid = await self._add_uri(url, options)
                    if result is AddResult.DUPLICATE:
                        duplicate_any = True
                        continue
                    if result is AddResult.FAILED or gid is None:
                        failed_any = True
                        continue
                    gid = await self._resolve_followed_by_gid(gid)
                    await db.aria2.upsert(gid, bangumi_id, category, dedup_key)
                    added_any = True
            if torrent_files:
                files = (
                    torrent_files
                    if isinstance(torrent_files, list)
                    else [torrent_files]
                )
                for f in files:
                    dedup_key = f"file:{hashlib.sha1(f).hexdigest()}"
                    existing_gid = await db.aria2.find_by_dedup_key(dedup_key)
                    if existing_gid:
                        stale = await self._dedup_record_is_stale(db, existing_gid)
                        if stale is None:
                            failed_any = True
                            continue
                        if not stale:
                            logger.debug("Skip already-added torrent file")
                            duplicate_any = True
                            continue
                    result, gid = await self._add_torrent_file(f, options)
                    if result is AddResult.DUPLICATE:
                        duplicate_any = True
                        continue
                    if result is AddResult.FAILED or gid is None:
                        failed_any = True
                        continue
                    gid = await self._resolve_followed_by_gid(gid)
                    await db.aria2.upsert(gid, bangumi_id, category, dedup_key)
                    added_any = True
        # 部分成功按 ADDED 报告（与 qB 的批量语义一致）：已经真正开始下载
        # 的任务必须让上层入库，否则会与 aria2 状态脱节；全部失败才算 FAILED。
        if added_any:
            return AddResult.ADDED
        if failed_any:
            return AddResult.FAILED
        if duplicate_any:
            return AddResult.DUPLICATE
        return AddResult.FAILED

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    async def torrents_info(self, status_filter, category, tag=None) -> list[dict]:
        try:
            active = await self._call("tellActive") or []
            waiting = await self._call("tellWaiting", [0, 1000]) or []
            stopped = await self._call("tellStopped", [0, 1000]) or []
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.error("Failed to query downloads: %s", e)
            return []
        raw = [*active, *waiting, *stopped]
        followed_by: dict[str, str] = {}
        for d in raw:
            gid = d.get("gid")
            follower = self._extract_followed_by_gid(d)
            if gid and follower:
                followed_by[gid] = follower
        gids = [followed_by.get(d["gid"], d["gid"]) for d in raw if d.get("gid")]
        async with Database() as db:
            for old_gid, new_gid in followed_by.items():
                await db.aria2.replace_gid(old_gid, new_gid)
            meta = await db.aria2.get_many(gids)

        allowed_statuses = (
            _STATUS_FILTER_MAP.get(status_filter) if status_filter else None
        )
        result = []
        for d in raw:
            gid = d.get("gid", "")
            aria2_status = d.get("status", "")
            if gid in followed_by:
                # 磁力元数据 stub：真实下载由 followedBy gid 表示。stub 的
                # status 是 "complete"，若不跳过会以完成态混进结果，让
                # 重命名循环拿元数据文件当正片处理，且 UI 出现重复条目。
                continue
            if allowed_statuses is not None and aria2_status not in allowed_statuses:
                continue
            info = meta.get(followed_by.get(gid, gid))
            torrent_category = info.category if info else None
            if category and torrent_category != category:
                continue
            tags_str = f"ab:{info.bangumi_id}" if info and info.bangumi_id else ""
            if tag and tag != tags_str:
                continue
            # aria2 JSON-RPC 的数值字段全是字符串（"0" 也是 truthy），必须先
            # 转 int 再判断，否则磁力链拉元数据阶段 totalLength "0" 会除零。
            total = int(d.get("totalLength", 0) or 0)
            completed = int(d.get("completedLength", 0) or 0)
            result.append(
                {
                    "hash": gid,
                    "name": self._extract_name(d),
                    "save_path": d.get("dir", ""),
                    "tags": tags_str,
                    "category": torrent_category or "",
                    "state": aria2_status,
                    "size": total,
                    "progress": completed / total if total > 0 else 0.0,
                    "dlspeed": int(d.get("downloadSpeed", 0) or 0),
                    "upspeed": int(d.get("uploadSpeed", 0) or 0),
                }
            )
        return result

    async def torrents_files(self, torrent_hash: str) -> list[dict]:
        try:
            files = await self._call("getFiles", [torrent_hash])
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.error("Failed to get files for %s: %s", torrent_hash, e)
            return []
        save_dir = ""
        try:
            status = await self._call("tellStatus", [torrent_hash, ["dir"]])
            save_dir = (status or {}).get("dir", "")
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.debug("Could not resolve dir for %s: %s", torrent_hash, e)
        async with Database() as db:
            renamed_paths = await db.aria2.get_renamed_paths(torrent_hash)
        result = []
        for f in files or []:
            path = f.get("path", "")
            rel = os.path.relpath(path, save_dir) if save_dir and path else path
            rel = self._translate_renamed_path(rel, renamed_paths)
            result.append({"name": rel, "size": int(f.get("length", 0) or 0)})
        return result

    # ------------------------------------------------------------------
    # Rename (filesystem move -- aria2 downloads land in a known local dir)
    # ------------------------------------------------------------------

    async def torrents_rename_file(
        self, torrent_hash, old_path, new_path, verify: bool = True
    ) -> bool:
        try:
            status = await self._call("tellStatus", [torrent_hash, ["dir"]])
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.warning(
                "Rename failed, cannot resolve save dir for %s: %s",
                torrent_hash,
                e,
            )
            return False
        save_dir = (status or {}).get("dir", "")
        if not save_dir:
            return False
        old_abs = os.path.join(save_dir, old_path)
        new_abs = os.path.join(save_dir, new_path)
        try:
            await asyncio.to_thread(self._move_file, old_abs, new_abs)
        except FileExistsError:
            logger.warning(
                "Refusing to overwrite existing file %s, rename of %s skipped",
                new_abs,
                old_abs,
            )
            return False
        except OSError as e:
            logger.warning("Failed to rename file %s -> %s: %s", old_abs, new_abs, e)
            return False
        if verify:
            exists = await asyncio.to_thread(os.path.exists, new_abs)
            if not exists:
                logger.debug("Rename reported success but %s is missing", new_abs)
                return False
        async with Database() as db:
            await db.aria2.set_renamed_path(torrent_hash, old_path, new_path)
        return True

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    async def torrents_delete(self, hash, delete_files: bool = True) -> bool:
        gids = self._normalize_hashes(hash)
        ok = True
        async with Database() as db:
            for gid in gids:
                save_dir = None
                try:
                    status = await self._call("tellStatus", [gid, ["dir"]])
                    save_dir = (status or {}).get("dir")
                except (Aria2RpcError, Aria2ConnectionError) as e:
                    logger.debug("Could not resolve dir for %s: %s", gid, e)

                if delete_files and save_dir:
                    try:
                        files = await self._call("getFiles", [gid])
                    except (Aria2RpcError, Aria2ConnectionError):
                        files = []
                    for f in files or []:
                        path = f.get("path")
                        if not path:
                            continue
                        try:
                            await asyncio.to_thread(
                                self._remove_file_and_empty_dirs, path, save_dir
                            )
                        except OSError as e:
                            logger.warning("Failed to delete file %s: %s", path, e)

                try:
                    await self._call("forceRemove", [gid])
                except Aria2RpcError as e:
                    if not self._is_not_found_error(e):
                        logger.error("Failed to remove %s: %s", gid, e)
                        ok = False
                except Aria2ConnectionError as e:
                    logger.error("Failed to remove %s: %s", gid, e)
                    ok = False

                await db.aria2.delete(gid)
        return ok

    async def torrents_pause(self, hashes: str | list[str]) -> None:
        for gid in self._normalize_hashes(hashes):
            try:
                await self._call("forcePause", [gid])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning("Failed to pause %s: %s", gid, e)

    async def torrents_resume(self, hashes: str | list[str]) -> None:
        for gid in self._normalize_hashes(hashes):
            try:
                await self._call("unpause", [gid])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning("Failed to resume %s: %s", gid, e)

    async def move_torrent(self, hashes, new_location) -> None:
        for gid in self._normalize_hashes(hashes):
            try:
                status = await self._call("tellStatus", [gid, ["dir"]])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning("Cannot move %s, status lookup failed: %s", gid, e)
                continue
            old_dir = (status or {}).get("dir")
            if not old_dir or os.path.normpath(old_dir) == os.path.normpath(
                new_location
            ):
                continue
            try:
                files = await self._call("getFiles", [gid])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning("Cannot move %s, file list failed: %s", gid, e)
                continue
            try:
                await asyncio.to_thread(
                    self._move_files, files or [], old_dir, new_location
                )
            except OSError as e:
                logger.warning("Failed to move files for %s: %s", gid, e)
                continue
            try:
                await self._call("changeOption", [gid, {"dir": new_location}])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.debug("changeOption dir failed for %s (non-fatal): %s", gid, e)

    async def set_category(self, _hash, category) -> None:
        async with Database() as db:
            for gid in self._normalize_hashes(_hash):
                await db.aria2.set_category(gid, category)

    async def add_tag(self, _hash: str, tag: str) -> None:
        """只认识 'ab:<bangumi_id>' 格式的 tag（用于 offset 关联），其余忽略。"""
        bangumi_id = self._parse_bangumi_id_from_tag(tag)
        if bangumi_id is None:
            logger.debug("Ignoring unsupported tag: %s", tag)
            return
        async with Database() as db:
            await db.aria2.upsert(_hash, bangumi_id=bangumi_id)

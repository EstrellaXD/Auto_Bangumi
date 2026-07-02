import asyncio
import hashlib
import logging
import os
import shutil
from typing import ClassVar

import httpx

from module.database import Database
from module.downloader.base import DownloaderCapabilities

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
    def _move_file(old_abs: str, new_abs: str) -> None:
        os.makedirs(os.path.dirname(new_abs), exist_ok=True)
        os.replace(old_abs, new_abs)

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

    async def _add_uri(self, url: str, options: dict) -> str | None:
        try:
            return await self._call("addUri", [[url], options])
        except Aria2RpcError as e:
            if self._is_duplicate_error(e):
                logger.debug("[Aria2] addUri reports duplicate: %s", e.message)
            else:
                logger.error("[Aria2] addUri failed for %s: %s", url, e)
            return None
        except Aria2ConnectionError as e:
            logger.error("[Aria2] addUri connection error for %s: %s", url, e)
            return None

    async def _add_torrent_file(self, data: bytes, options: dict) -> str | None:
        import base64

        b64 = base64.b64encode(data).decode()
        try:
            return await self._call("addTorrent", [b64, [], options])
        except Aria2RpcError as e:
            if self._is_duplicate_error(e):
                logger.debug("[Aria2] addTorrent reports duplicate: %s", e.message)
            else:
                logger.error("[Aria2] addTorrent failed: %s", e)
            return None
        except Aria2ConnectionError as e:
            logger.error("[Aria2] addTorrent connection error: %s", e)
            return None

    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ) -> bool:
        """添加下载任务，返回 True 当且仅当真的新增了至少一个任务。

        去重优先靠本地的 dedup_key（url 或种子内容 hash）判断"已经添加过"，
        aria2 RPC 报错里带 already/duplicate 字样时也当作重复处理（见
        ``_is_duplicate_error``）——这样调用方（DownloadClient.add_torrent）
        才能像 qBittorrent 一样区分"新增成功"和"之前加过了"。
        """
        bangumi_id = self._parse_bangumi_id_from_tag(tags)
        options = {"dir": save_path}
        added_any = False
        async with Database() as db:
            if torrent_urls:
                urls = (
                    torrent_urls if isinstance(torrent_urls, list) else [torrent_urls]
                )
                for url in urls:
                    dedup_key = f"url:{url}"
                    if await db.aria2.find_by_dedup_key(dedup_key):
                        logger.debug("[Aria2] Skip already-added url: %s", url)
                        continue
                    gid = await self._add_uri(url, options)
                    if gid is None:
                        continue
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
                    if await db.aria2.find_by_dedup_key(dedup_key):
                        logger.debug("[Aria2] Skip already-added torrent file")
                        continue
                    gid = await self._add_torrent_file(f, options)
                    if gid is None:
                        continue
                    await db.aria2.upsert(gid, bangumi_id, category, dedup_key)
                    added_any = True
        return added_any

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    async def torrents_info(self, status_filter, category, tag=None) -> list[dict]:
        try:
            active = await self._call("tellActive") or []
            waiting = await self._call("tellWaiting", [0, 1000]) or []
            stopped = await self._call("tellStopped", [0, 1000]) or []
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.error("[Aria2] Failed to query downloads: %s", e)
            return []
        raw = [*active, *waiting, *stopped]
        gids = [d["gid"] for d in raw if d.get("gid")]
        async with Database() as db:
            meta = await db.aria2.get_many(gids)

        allowed_statuses = (
            _STATUS_FILTER_MAP.get(status_filter) if status_filter else None
        )
        result = []
        for d in raw:
            gid = d.get("gid", "")
            aria2_status = d.get("status", "")
            if allowed_statuses is not None and aria2_status not in allowed_statuses:
                continue
            info = meta.get(gid)
            torrent_category = info.category if info else None
            if category and torrent_category != category:
                continue
            tags_str = f"ab:{info.bangumi_id}" if info and info.bangumi_id else ""
            if tag and tag != tags_str:
                continue
            result.append(
                {
                    "hash": gid,
                    "name": self._extract_name(d),
                    "save_path": d.get("dir", ""),
                    "tags": tags_str,
                    "category": torrent_category or "",
                    "state": aria2_status,
                    "size": int(d.get("totalLength", 0) or 0),
                    "progress": (
                        int(d.get("completedLength", 0) or 0) / int(d["totalLength"])
                        if d.get("totalLength")
                        else 0
                    ),
                    "dlspeed": int(d.get("downloadSpeed", 0) or 0),
                    "upspeed": int(d.get("uploadSpeed", 0) or 0),
                }
            )
        return result

    async def torrents_files(self, torrent_hash: str) -> list[dict]:
        try:
            files = await self._call("getFiles", [torrent_hash])
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.error("[Aria2] Failed to get files for %s: %s", torrent_hash, e)
            return []
        save_dir = ""
        try:
            status = await self._call("tellStatus", [torrent_hash, ["dir"]])
            save_dir = (status or {}).get("dir", "")
        except (Aria2RpcError, Aria2ConnectionError) as e:
            logger.debug("[Aria2] Could not resolve dir for %s: %s", torrent_hash, e)
        result = []
        for f in files or []:
            path = f.get("path", "")
            rel = os.path.relpath(path, save_dir) if save_dir and path else path
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
                "[Aria2] Rename failed, cannot resolve save dir for %s: %s",
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
        except OSError as e:
            logger.warning(
                "[Aria2] Failed to rename file %s -> %s: %s", old_abs, new_abs, e
            )
            return False
        if verify:
            exists = await asyncio.to_thread(os.path.exists, new_abs)
            if not exists:
                logger.debug(
                    "[Aria2] Rename reported success but %s is missing", new_abs
                )
                return False
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
                    logger.debug("[Aria2] Could not resolve dir for %s: %s", gid, e)

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
                            logger.warning(
                                "[Aria2] Failed to delete file %s: %s", path, e
                            )

                try:
                    await self._call("forceRemove", [gid])
                except Aria2RpcError as e:
                    if not self._is_not_found_error(e):
                        logger.error("[Aria2] Failed to remove %s: %s", gid, e)
                        ok = False
                except Aria2ConnectionError as e:
                    logger.error("[Aria2] Failed to remove %s: %s", gid, e)
                    ok = False

                await db.aria2.delete(gid)
        return ok

    async def torrents_pause(self, hashes: str | list[str]) -> None:
        for gid in self._normalize_hashes(hashes):
            try:
                await self._call("forcePause", [gid])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning("[Aria2] Failed to pause %s: %s", gid, e)

    async def torrents_resume(self, hashes: str | list[str]) -> None:
        for gid in self._normalize_hashes(hashes):
            try:
                await self._call("unpause", [gid])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning("[Aria2] Failed to resume %s: %s", gid, e)

    async def move_torrent(self, hashes, new_location) -> None:
        for gid in self._normalize_hashes(hashes):
            try:
                status = await self._call("tellStatus", [gid, ["dir"]])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning(
                    "[Aria2] Cannot move %s, status lookup failed: %s", gid, e
                )
                continue
            old_dir = (status or {}).get("dir")
            if not old_dir or os.path.normpath(old_dir) == os.path.normpath(
                new_location
            ):
                continue
            try:
                files = await self._call("getFiles", [gid])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.warning("[Aria2] Cannot move %s, file list failed: %s", gid, e)
                continue
            try:
                await asyncio.to_thread(
                    self._move_files, files or [], old_dir, new_location
                )
            except OSError as e:
                logger.warning("[Aria2] Failed to move files for %s: %s", gid, e)
                continue
            try:
                await self._call("changeOption", [gid, {"dir": new_location}])
            except (Aria2RpcError, Aria2ConnectionError) as e:
                logger.debug(
                    "[Aria2] changeOption dir failed for %s (non-fatal): %s", gid, e
                )

    async def set_category(self, _hash, category) -> None:
        async with Database() as db:
            for gid in self._normalize_hashes(_hash):
                await db.aria2.set_category(gid, category)

    async def add_tag(self, _hash: str, tag: str) -> None:
        """只认识 'ab:<bangumi_id>' 格式的 tag（用于 offset 关联），其余忽略。"""
        bangumi_id = self._parse_bangumi_id_from_tag(tag)
        if bangumi_id is None:
            logger.debug("[Aria2] Ignoring unsupported tag: %s", tag)
            return
        async with Database() as db:
            await db.aria2.upsert(_hash, bangumi_id=bangumi_id)

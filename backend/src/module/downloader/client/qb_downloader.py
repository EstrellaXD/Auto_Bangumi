import asyncio
import hashlib
import json
import logging
import re
from typing import ClassVar

import httpx

from module.ab_decorator import qb_connect_failed_wait
from module.downloader.base import (
    AddResult,
    DownloaderCapabilities,
    RenameOutcome,
    RenameResult,
)

logger = logging.getLogger(__name__)

_MAGNET_BTIH_RE = re.compile(r"xt=urn:btih:([0-9A-Fa-f]{40}|[A-Za-z2-7]{32})")


def _torrent_infohash(data: bytes) -> str | None:
    """从 .torrent 字节中提取 v1 infohash（bencoded ``info`` 字典的 SHA-1）。

    qB ≤5.1 对重复上传只回笼统的 "Fails."——要确认"其实已存在"就得拿文件
    自己算 hash 去查。手写极简 bencode 游标（只需定位 info 值的字节区间，
    不需要完整解码），损坏/非 bencode 输入返回 None。
    """

    def _skip(i: int) -> int:
        """返回从 i 开始的 bencode 元素的结束下标（exclusive）。"""
        c = data[i : i + 1]
        if c == b"i":
            return data.index(b"e", i) + 1
        if c in (b"l", b"d"):
            i += 1
            while data[i : i + 1] != b"e":
                i = _skip(i)
            return i + 1
        colon = data.index(b":", i)
        return colon + 1 + int(data[i:colon])

    try:
        if data[:1] != b"d":
            return None
        i = 1
        while data[i : i + 1] != b"e":
            colon = data.index(b":", i)
            key_len = int(data[i:colon])
            key = data[colon + 1 : colon + 1 + key_len]
            i = colon + 1 + key_len
            end = _skip(i)
            if key == b"info":
                if data[i : i + 1] != b"d":
                    return None
                return hashlib.sha1(data[i:end]).hexdigest()
            i = end
        return None
    except (ValueError, IndexError):
        return None


class QbDownloader:
    capabilities: ClassVar[DownloaderCapabilities] = DownloaderCapabilities(
        can_query=True,
        can_rename=True,
        can_manage=True,
        can_rss_rules=True,
    )

    def __init__(self, host: str, username: str, password: str, ssl: bool):
        if "://" not in host:
            scheme = "https" if ssl else "http"
            self.host = f"{scheme}://{host}"
        else:
            self.host = host
        self.username = username
        self.password = password
        self.ssl = ssl
        self._client: httpx.AsyncClient | None = None
        self._authed = False
        # 最近一次 auth 失败的原因（unreachable | credentials | banned），
        # 供上层（checker/startup 等待循环）区分故障类型；成功后清空。
        self.last_auth_error: str | None = None
        # Single-flights the reactive 403 re-login below so concurrent
        # requests don't each fire their own login attempt and trip
        # qBittorrent's IP ban (#1046-adjacent).
        self._auth_lock = asyncio.Lock()
        # 每完成一次真实登录尝试 +1：让排在锁后的并发等待者识别"我等待期间
        # 已有一次登录被凭据拒绝"，从而不再补发自己的 POST。
        self._auth_generation = 0
        # qB 5.0 把 torrents/pause|resume 改名为 stop|start 且无别名（旧名
        # 404），4.x 则没有新名。记住哪套命名有效；None = 还没探测过。
        self._uses_stop_start: bool | None = None

    def _url(self, endpoint: str) -> str:
        return f"{self.host}/api/v2/{endpoint}"

    def _new_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
        # Keepalive_expiry keeps idle TCP sockets short-lived so they can't
        # outlive a proxy / NAS idle-reap, which would otherwise surface as
        # "Server disconnected without sending a response" when the next
        # renamer cycle reuses the pool (#984). max_connections caps parallel
        # load on the downloader and anything fronting it.
        limits = httpx.Limits(
            max_keepalive_connections=5,
            max_connections=10,
            keepalive_expiry=30.0,
        )
        # Never verify certificates - self-signed certs are the norm for
        # home-server / NAS / Docker qBittorrent setups.
        return httpx.AsyncClient(timeout=timeout, limits=limits, verify=False)

    async def auth(self, retry=3):
        # Session reuse: a live, already-authenticated client short-circuits so
        # repeated operations don't re-login every cycle (#1039 / #900).
        if self._client is not None and self._authed:
            return True
        # 单飞：并发的 loop tick 同时 auth() 时只发一次 login POST——失败的
        # 并发登录会各自计入 qB 的 WebUI IP ban 阈值（默认 5 次即封禁）。
        generation = self._auth_generation
        async with self._auth_lock:
            if self._client is not None and self._authed:
                return True
            if (
                generation != self._auth_generation
                and self.last_auth_error == "credentials"
            ):
                # 等锁期间已有一次真实登录被凭据拒绝：共享这个否定结果，
                # 不再补发自己的 POST。之后的全新 auth() 调用（如 checker
                # 主动探测）不受影响，仍可重试并在成功后清除失败原因。
                return False
            return await self._locked_auth(retry)

    async def _locked_auth(self, retry=3):
        """auth() 的主体；调用方必须已持有 ``_auth_lock``。"""
        if self._client is not None and self._authed:
            return True
        try:
            return await self._login_attempt(retry)
        finally:
            # 尝试结束后才 +1：在本次尝试期间排队的等待者捕获的是旧值，
            # 醒来后据此识别"结果已出"，共享失败结论而非重复 POST。
            self._auth_generation += 1

    async def _login_attempt(self, retry=3):
        times = 0
        use_https = self.host.startswith("https://")
        if self._client is None:
            self._client = self._new_client()
        while times < retry:
            try:
                resp = await self._client.post(
                    self._url("auth/login"),
                    data={"username": self.username, "password": self.password},
                )
                # qBittorrent < 5.2 answers 200 + "Ok." / "Fails.";
                # qBittorrent >= 5.2 answers 204 with an empty body on success
                # (#1044). Keep the positive body check for 200 so a proxy or
                # non-qB service answering 200 + HTML is not mistaken for a
                # successful login.
                if (
                    resp.status_code == 200 and resp.text.startswith("Ok")
                ) or resp.status_code == 204:
                    self._authed = True
                    self.last_auth_error = None
                    return True
                elif (
                    resp.status_code == 200 and resp.text.startswith("Fails")
                ) or resp.status_code == 401:
                    # 密码错误重试只会触发 qB 的 WebUI IP ban（默认 5 次失败
                    # 即封禁，之后全部 403），必须立刻停下并明确提示。
                    self.last_auth_error = "credentials"
                    logger.error(
                        "qBittorrent rejected the username or password. "
                        "Check the downloader credentials in AutoBangumi settings; "
                        "not retrying to avoid a WebUI IP ban."
                    )
                    break
                elif resp.status_code == 403:
                    self.last_auth_error = "banned"
                    logger.error("Login refused by qBittorrent Server")
                    logger.info("Please release the IP in qBittorrent Server")
                    break
                else:
                    self.last_auth_error = "unreachable"
                    logger.error(
                        f"Can't login qBittorrent Server {self.host} by {self.username}, retry in 5 seconds."
                    )
                    await asyncio.sleep(5)
                    times += 1
            except httpx.ConnectError as e:
                self.last_auth_error = "unreachable"
                if use_https:
                    logger.error(
                        "Cannot connect to qBittorrent Server via HTTPS. "
                        "If your qBittorrent uses plain HTTP, disable SSL in download settings."
                    )
                else:
                    logger.error("Cannot connect to qBittorrent Server")
                logger.info("Please check the IP and port in WebUI settings")
                logger.debug("Connection error detail: %s", e)
                await asyncio.sleep(10)
                times += 1
            except Exception as e:
                self.last_auth_error = "unreachable"
                if use_https and "ssl" in str(e).lower():
                    logger.error(
                        "TLS/SSL error connecting to qBittorrent. "
                        "If your qBittorrent uses plain HTTP, disable SSL in download settings."
                    )
                else:
                    logger.error(f"Unknown error: {e}")
                break
        return False

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Issue a request, re-authenticating once if the session expired.

        qBittorrent answers 403 when the session cookie is no longer valid
        (e.g. the server restarted or reaped the session). Since we now keep one
        long-lived session, force a single re-login and retry the request once.
        The re-login is single-flighted behind ``_auth_lock`` so a burst of
        concurrent requests hitting 403 at once triggers one login attempt,
        not one per request (a login storm can get the caller's IP banned by
        qBittorrent). Only retry the original request if re-auth succeeded.
        """
        assert self._client is not None, "QbDownloader.auth() must run first"
        resp = await self._client.request(method, self._url(endpoint), **kwargs)
        if resp.status_code == 403:
            self._authed = False
            async with self._auth_lock:
                # Another waiter may have already refreshed the session while
                # we were blocked on the lock.
                if not self._authed:
                    await self._locked_auth()
            if not self._authed:
                raise ConnectionError(
                    f"Re-authentication to qBittorrent at {self.host} "
                    "failed; not retrying request to avoid a login storm."
                )
            resp = await self._client.request(method, self._url(endpoint), **kwargs)
        return resp

    async def _get(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._request("GET", endpoint, **kwargs)

    async def _post(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self._request("POST", endpoint, **kwargs)

    async def logout(self):
        if self._client:
            try:
                await self._client.post(self._url("auth/logout"))
            except (
                httpx.ConnectError,
                httpx.RequestError,
                httpx.TimeoutException,
            ) as e:
                logger.debug("Logout request failed (non-critical): %s", e)
            await self._client.aclose()
            self._client = None
        self._authed = False

    async def check_host(self):
        try:
            resp = await self._get("app/version")
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.RequestError):
            return False

    def check_rss(self, rss_link: str):
        pass

    @qb_connect_failed_wait
    async def prefs_init(self, prefs):
        resp = await self._post(
            "app/setPreferences",
            data={"json": json.dumps(prefs)},
        )
        return resp

    @qb_connect_failed_wait
    async def get_app_prefs(self):
        resp = await self._get("app/preferences")
        return resp.json()

    async def add_category(self, category):
        await self._post(
            "torrents/createCategory",
            data={"category": category, "savePath": ""},
        )

    @qb_connect_failed_wait
    async def torrents_info(self, status_filter, category, tag=None):
        params = {}
        # qB 5.0 把 filter=paused 改名为 stopped，且未知 filter 值会静默
        # 退化成 All（返回全部种子）——服务端过滤无法跨版本，改为不带
        # filter 拉取后按 state 本地过滤。其余值（completed 等）未改名。
        paused_filter = status_filter in ("paused", "stopped")
        if status_filter and not paused_filter:
            params["filter"] = status_filter
        if category:
            params["category"] = category
        if tag:
            params["tag"] = tag
        resp = await self._get("torrents/info", params=params)
        torrents = resp.json()
        if paused_filter:
            torrents = [
                t
                for t in torrents
                if t.get("state", "").startswith(("paused", "stopped"))
            ]
        return torrents

    async def torrent_exists(self, torrent_hash: str) -> bool | None:
        """Query one hash without confusing a failed request with absence."""

        try:
            resp = await self._get("torrents/info", params={"hashes": torrent_hash})
            if resp.status_code >= 300:
                logger.warning(
                    "Could not verify qBittorrent task %s: HTTP %s",
                    torrent_hash,
                    resp.status_code,
                )
                return None
            payload = resp.json()
        except (ConnectionError, OSError, ValueError, httpx.RequestError) as e:
            logger.warning("Could not verify qBittorrent task %s: %s", torrent_hash, e)
            return None
        return isinstance(payload, list) and any(
            str(item.get("hash", "")).lower() == torrent_hash.lower()
            for item in payload
            if isinstance(item, dict)
        )

    @qb_connect_failed_wait
    async def torrents_files(self, torrent_hash: str):
        resp = await self._get("torrents/files", params={"hash": torrent_hash})
        return resp.json()

    async def _urls_already_added(self, torrent_urls) -> bool:
        """尽力确认"Fails."是否因为任务已存在：从磁力链提取 btih 并查询 qB。

        只有全部 URL 都是可提取 hash 的磁力链、且每个 hash 都已在 qB 中时才
        返回 True；.torrent URL 无法事先得知 hash，返回 False（按失败处理）。
        """
        urls = (
            torrent_urls
            if isinstance(torrent_urls, list)
            else [torrent_urls] if torrent_urls else []
        )
        if not urls:
            return False
        hashes: list[str] = []
        for url in urls:
            m = _MAGNET_BTIH_RE.search(url or "")
            if not m:
                return False
            btih = m.group(1)
            if len(btih) == 32:  # base32 -> hex
                import base64

                try:
                    btih = base64.b32decode(btih.upper()).hex()
                except ValueError:
                    return False
            hashes.append(btih.lower())
        return await self._hashes_all_present(hashes)

    async def _files_already_added(self, torrent_files) -> bool:
        """尽力确认"Fails."是否因为任务已存在：对 .torrent 文件字节计算
        infohash 并查询 qB。只有全部文件都能算出 hash、且每个 hash 都已在
        qB 中时才返回 True；算不出 hash（损坏文件）返回 False（按失败处理）。
        """
        if not torrent_files:
            return False
        file_list = (
            torrent_files if isinstance(torrent_files, list) else [torrent_files]
        )
        hashes: list[str] = []
        for f in file_list:
            infohash = _torrent_infohash(f)
            if infohash is None:
                return False
            hashes.append(infohash)
        return await self._hashes_all_present(hashes)

    async def _hashes_all_present(self, hashes: list[str]) -> bool:
        if not hashes:
            return False
        try:
            resp = await self._get("torrents/info", params={"hashes": "|".join(hashes)})
            found = {t.get("hash", "").lower() for t in resp.json()}
            return set(hashes) <= found
        except (httpx.RequestError, ValueError):
            return False

    @staticmethod
    def _parse_add_response_json(resp: httpx.Response) -> dict | None:
        """qB >= 5.2 的 torrents/add 回 JSON 计数；旧版本回 "Ok."/"Fails."。
        不是该结构（如代理返回的 HTML 错误页）时返回 None，走通用失败路径。
        """
        try:
            data = resp.json()
        except ValueError:
            return None
        if isinstance(data, dict) and "success_count" in data:
            return data
        return None

    async def add_torrents(
        self, torrent_urls, torrent_files, save_path, category, tags=None
    ):
        data = {
            "savepath": save_path,
            "category": category,
            # qB 5.0 把 paused 参数改名为 stopped；双方都静默忽略未知参数，
            # 两个都发才能覆盖所有版本。
            "paused": "false",
            "stopped": "false",
            "autoTMM": "false",
            "contentLayout": "NoSubfolder",
        }
        if tags:
            data["tags"] = tags
        files = {}
        if torrent_urls:
            if isinstance(torrent_urls, list):
                data["urls"] = "\n".join(torrent_urls)
            else:
                data["urls"] = torrent_urls
        if torrent_files:
            if isinstance(torrent_files, list):
                for i, f in enumerate(torrent_files):
                    files[f"torrents_{i}"] = (
                        f"torrent_{i}.torrent",
                        f,
                        "application/x-bittorrent",
                    )
            else:
                files["torrents"] = (
                    "torrent.torrent",
                    torrent_files,
                    "application/x-bittorrent",
                )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = await self._post(
                    "torrents/add",
                    data=data,
                    files=files if files else None,
                )
                if resp.status_code == 200 and resp.text == "Ok.":
                    return AddResult.ADDED
                if resp.status_code in (200, 202):
                    # qBittorrent >= 5.2 返回逐种子 JSON 结果：
                    # {"added_torrent_ids": [...], "failure_count": 0,
                    #  "pending_count": 0, "success_count": 1}
                    # URL 形式的 add 是异步下载，qB 回 202 + pending_count>0
                    # ——已受理即算成功。部分成功也按 ADDED 处理：与旧版
                    # "Ok."（>=1 成功即 Ok.）和 aria2 客户端的约定一致，
                    # 否则已投递的种子会被整批记成失败。计数全 0 说明什么
                    # 都没发生，不算成功。
                    counts = self._parse_add_response_json(resp)
                    if counts is not None and (
                        counts.get("success_count") or counts.get("pending_count")
                    ):
                        return AddResult.ADDED
                    # "Fails."（qB <= 5.1）与 JSON failure_count > 0 都覆盖
                    # 所有被拒绝的 add（重复、种子损坏、磁力链无法解析……），
                    # 不能一律当重复——否则损坏种子会被记成已下载、永远不
                    # 重试。只有能通过 hash（磁力链的 btih 或 .torrent 文件
                    # 算出的 infohash）确认任务已存在时才归类为重复，
                    # 其余按失败抛出让上层重试。
                    if await self._urls_already_added(
                        torrent_urls
                    ) or await self._files_already_added(torrent_files):
                        return AddResult.DUPLICATE
                    raise ConnectionError(
                        "qBittorrent rejected torrent add "
                        f"({resp.status_code} {resp.text!r}) "
                        "and no matching torrent found"
                    )
                if resp.status_code == 409:
                    # qBittorrent >= 5.2：全部为重复/失败且无 pending 时回
                    # 409 Conflict (qbittorrent/qBittorrent#18361)。文件上传
                    # 是同步解析的，损坏文件走 415（BadData），所以文件的
                    # 409 就是重复；磁力链尽力用 hash 确认，确认不了的按
                    # 失败抛出，避免把损坏的 add 记成已下载、永远不重试。
                    if torrent_files is not None or await self._urls_already_added(
                        torrent_urls
                    ):
                        return AddResult.DUPLICATE
                    raise ConnectionError(
                        "qBittorrent rejected torrent add (409 Conflict) "
                        "and no matching torrent found"
                    )
                raise ConnectionError(
                    "qBittorrent rejected torrent add: "
                    f"HTTP {resp.status_code} {resp.text!r}"
                )
            except (httpx.ReadError, httpx.ConnectError, httpx.RequestError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Network error adding torrent (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(2)
                else:
                    logger.error(
                        f"Failed to add torrent after {max_retries} attempts: {e}"
                    )
                    raise

    async def get_torrents_by_tag(self, tag: str) -> list[dict]:
        resp = await self._get("torrents/info", params={"tag": tag})
        return resp.json()

    @staticmethod
    def _normalize_hashes(hashes: str | list[str] | tuple[str, ...]) -> str:
        """qBittorrent expects one pipe-joined "hashes" field; a Python list
        would be form-encoded as repeated fields and silently ignored (#1046).
        Centralized here so every hashes-taking endpoint applies it the same
        way.
        """
        return "|".join(hashes) if isinstance(hashes, (list, tuple)) else hashes

    async def torrents_delete(self, hash, delete_files: bool = True) -> bool:
        hashes = self._normalize_hashes(hash)
        resp = await self._post(
            "torrents/delete",
            data={"hashes": hashes, "deleteFiles": str(delete_files).lower()},
        )
        # qB 5.2 起空响应体统一回 204，不能用 ==200 判定
        if resp.status_code >= 300:
            logger.error(
                "Failed to delete torrents %s: HTTP %s",
                hashes,
                resp.status_code,
            )
            return False
        return True

    async def _start_stop(
        self, hashes: str | list[str], modern: str, legacy: str
    ) -> None:
        """qB 5.0 把 pause/resume 改名为 stop/start 且无别名（旧名 404），
        4.x 没有新名。先试上次成功的那套命名（默认新名），404 时换另一套
        并记住。操作幂等，重发一次无副作用。
        """
        data = {"hashes": self._normalize_hashes(hashes)}
        prefer_modern = self._uses_stop_start is not False
        first, second = (modern, legacy) if prefer_modern else (legacy, modern)
        used = first
        resp = await self._post(f"torrents/{first}", data=data)
        if resp.status_code == 404:
            used = second
            resp = await self._post(f"torrents/{second}", data=data)
            if resp.status_code != 404:
                self._uses_stop_start = second == modern
        else:
            self._uses_stop_start = first == modern
        if resp.status_code >= 300:
            logger.error(
                "Failed to %s torrents %s: HTTP %s",
                used,
                data["hashes"],
                resp.status_code,
            )

    async def torrents_pause(self, hashes: str | list[str]):
        await self._start_stop(hashes, "stop", "pause")

    async def torrents_resume(self, hashes: str | list[str]):
        await self._start_stop(hashes, "start", "resume")

    async def torrents_rename_file(
        self, torrent_hash, old_path, new_path, verify: bool = True
    ) -> RenameResult:
        try:
            resp = await self._post(
                "torrents/renameFile",
                data={"hash": torrent_hash, "oldPath": old_path, "newPath": new_path},
            )
            if resp.status_code == 409:
                logger.debug("Conflict409Error: %s >> %s", old_path, new_path)
                return RenameResult(
                    RenameOutcome.DESTINATION_EXISTS,
                    detail="qBittorrent rejected rename with HTTP 409",
                )
            # qB 5.2 对成功的 renameFile 回 204（空响应体全局改为 204）
            if resp.status_code >= 300:
                return RenameResult(
                    RenameOutcome.RETRYABLE_FAILURE,
                    detail=f"qBittorrent rename returned HTTP {resp.status_code}",
                )

            if not verify:
                return RenameResult(RenameOutcome.RENAMED)

            # Verify the rename actually happened by checking file list
            # qBittorrent can return 200 but delay the actual rename (e.g., while seeding)
            # Use exponential backoff: 0.1s, 0.2s, 0.4s (max 3 attempts)
            for attempt in range(3):
                delay = 0.1 * (2**attempt)
                await asyncio.sleep(delay)
                files = await self.torrents_files(torrent_hash)
                if any(f.get("name") == new_path for f in files):
                    return RenameResult(RenameOutcome.RENAMED)
                # new_path 未出现（旧名仍在，或两个名字都不在列表里）一律不算
                # 成功：盲目返回 True 会让 renamer 每周期重复改名 + 发通知
                # (#754/#749)。返回 False 由调用方走 _PENDING_RENAME_COOLDOWN 退避。
                if attempt == 2:
                    logger.debug(
                        "Rename API returned 200 but %s never appeared "
                        "(rename of %s)",
                        new_path,
                        old_path,
                    )
            return RenameResult(
                RenameOutcome.RETRYABLE_FAILURE,
                detail="qBittorrent did not expose the target path after rename",
            )
        except (httpx.ConnectError, httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning(f"Failed to rename file {old_path}: {e}")
            return RenameResult(RenameOutcome.RETRYABLE_FAILURE, detail=str(e))

    async def rss_add_feed(self, url, item_path):
        resp = await self._post(
            "rss/addFeed",
            data={"url": url, "path": item_path},
        )
        if resp.status_code == 409:
            logger.warning(f"RSS feed {url} already exists")

    async def rss_remove_item(self, item_path):
        resp = await self._post(
            "rss/removeItem",
            data={"path": item_path},
        )
        if resp.status_code == 409:
            logger.warning(f"RSS item {item_path} does not exist")

    async def rss_get_feeds(self):
        resp = await self._get("rss/items")
        return resp.json()

    async def rss_set_rule(self, rule_name, rule_def):
        await self._post(
            "rss/setRule",
            data={"ruleName": rule_name, "ruleDef": json.dumps(rule_def)},
        )

    async def move_torrent(self, hashes, new_location):
        await self._post(
            "torrents/setLocation",
            data={"hashes": self._normalize_hashes(hashes), "location": new_location},
        )

    async def get_download_rule(self):
        resp = await self._get("rss/rules")
        return resp.json()

    async def get_torrent_path(self, _hash):
        resp = await self._get("torrents/info", params={"hashes": _hash})
        torrents = resp.json()
        if torrents:
            return torrents[0].get("save_path", "")
        return ""

    async def set_category(self, _hash, category):
        hashes = self._normalize_hashes(_hash)
        resp = await self._post(
            "torrents/setCategory",
            data={"hashes": hashes, "category": category},
        )
        if resp.status_code == 409:
            logger.warning(f"Category {category} does not exist")
            await self.add_category(category)
            await self._post(
                "torrents/setCategory",
                data={"hashes": hashes, "category": category},
            )

    async def check_connection(self):
        resp = await self._get("app/version")
        return resp.text

    async def remove_rule(self, rule_name):
        await self._post(
            "rss/removeRule",
            data={"ruleName": rule_name},
        )

    async def add_tag(self, _hash, tag):
        await self._post(
            "torrents/addTags",
            data={"hashes": _hash, "tags": tag},
        )

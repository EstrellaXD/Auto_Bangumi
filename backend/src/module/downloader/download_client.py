import asyncio
import logging
from collections import defaultdict
from contextlib import AsyncExitStack
from urllib.parse import urlparse

from ab_sdk import points
from ab_sdk.ingest import AddRequest
from module.conf import settings
from module.models import Bangumi, Torrent
from module.models.config import DOWNLOADER_POINT, DownloaderInstance
from module.network import RequestContent
from module.plugin import host as plugin_host
from module.plugin.views import bangumi_info, torrent_info

from .base import (
    AddResult,
    DownloaderClient,
    DownloaderConnection,
    RenameOutcome,
    RenameResult,
)
from .path import gen_save_path

logger = logging.getLogger(__name__)

# 同一主机批量抓取 .torrent 文件的请求间隔（#1052）。批量收集整季时并发抓取
# 会触发 nyaa 等站点的 429 限流；与 rss/engine.py 的 RSS_PER_HOST_DELAY 同思路，
# 但这里是收集接口内的一次性批量抓取，取 1s 以控制接口延迟（24 集约 +23s）。
TORRENT_FETCH_PER_HOST_DELAY = 1.0


async def _fetch_torrent_files(
    req: RequestContent, torrents: list[Torrent]
) -> list[bytes]:
    """抓取种子文件内容：同主机串行加延时，不同主机并行，失败项丢弃（#1052）。"""
    by_host: dict[str, list[Torrent]] = defaultdict(list)
    for t in torrents:
        by_host[urlparse(t.url).netloc].append(t)

    async def _fetch_host_group(items: list[Torrent]) -> list[bytes]:
        files: list[bytes] = []
        for i, t in enumerate(items):
            if i and TORRENT_FETCH_PER_HOST_DELAY:
                await asyncio.sleep(TORRENT_FETCH_PER_HOST_DELAY)
            content = await req.get_content(t.url)
            if content is not None:
                files.append(content)
        return files

    groups = await asyncio.gather(
        *[_fetch_host_group(items) for items in by_host.values()]
    )
    return [f for group in groups for f in group]


def _valid_add_request(request: AddRequest) -> bool:
    """宿主直接使用这些字段；类型不对的结果按钩子失败处理（str 标签也拒绝）。"""
    return (
        isinstance(request.save_path, (str, type(None)))
        and isinstance(request.category, str)
        and isinstance(request.tags, (tuple, list))
        and all(isinstance(t, str) for t in request.tags)
    )


async def _apply_adding_hooks(
    torrent: Torrent | list[Torrent],
    bangumi: Bangumi,
    save_path: str,
    category: str,
    tags: str | None,
) -> tuple[str, str, str | None]:
    """``torrent.adding``：插件修改保存路径、分类与标签。

    ``ab:<id>`` 标签是重命名时定位番剧的依据，钩子删掉时补回并告警。
    """
    runner = plugin_host.hook_runner(points.TORRENT_ADDING)
    if runner is None:
        return save_path, category, tags
    torrents = torrent if isinstance(torrent, list) else [torrent]
    request = AddRequest(
        bangumi=bangumi_info(bangumi),
        torrents=tuple(torrent_info(t) for t in torrents),
        save_path=save_path,
        category=category,
        tags=tuple(tags.split(",")) if tags else (),
    )
    result = await runner.transform(
        points.TORRENT_ADDING, request, expect=AddRequest, check=_valid_add_request
    )
    new_tags = [t.strip() for t in result.tags if t.strip()]
    if tags and tags not in new_tags:
        logger.warning(
            "torrent.adding removed required tag %s for %s; restored",
            tags,
            bangumi.official_title,
        )
        new_tags.insert(0, tags)
    return result.save_path, result.category, ",".join(new_tags) or None


# ---------------------------------------------------------------------------
# Module-level concrete-client cache (session reuse, #1039 / #900)
#
# Every ``async with DownloadClient()`` used to spin up a fresh concrete client
# and log in on enter / log out on exit -- one qB login+logout per operation,
# roughly once a minute from the rename loop. The cache keeps a single concrete
# client alive across operations, keyed by the connection-relevant settings.
#
# Closing a concrete client while another overlapping ``async with
# DownloadClient()`` block is still using it (mid-request) would kill that
# request out from under it. `_active_holders` reference-counts how many
# entered-but-not-yet-exited blocks currently hold each client (keyed by
# ``id(client)``); a client is only actually logged out once its count drops
# to zero -- either immediately (nobody holds it) or deferred to whichever
# block's ``__aexit__`` is the last to let go (`_pending_close`).
# `_bookkeeping_lock` serializes reads/writes of this shared state across the
# awaits in ``__aenter__``/``__aexit__``.
# ---------------------------------------------------------------------------
# 实例 id → (连接设置 key, 具体客户端)。每个下载器实例各缓存一个客户端。
_client_cache: dict[str, tuple[tuple, DownloaderClient]] = {}
_stale_clients: list[DownloaderClient] = []
_active_holders: dict[int, int] = {}
_pending_close: set[int] = set()
_bookkeeping_lock = asyncio.Lock()
# 凭据被服务端明确拒绝后的闩锁：实例 id → 失败时的连接设置 key。命中时 enter
# 直接失败、不再发 login POST——每个 tick 重试一次登录，约 5 次即触发 qB 的
# WebUI IP ban。设置变更（key 不同）自然解锁；同值重存经
# clear_credential_latch()（AppContext.reload_settings）解锁。
_credential_failed: dict[str, tuple] = {}

# Warn at most once per (client type, operation) when a backend cannot perform
# an operation, so aria2 users are not spammed every rename cycle.
_warned_unsupported: set[tuple[str, str]] = set()


def downloader_ids() -> list[str]:
    """所有下载器实例 id（配置顺序）。"""
    return [i.id for i in settings.plugins.instances if i.point == DOWNLOADER_POINT]


def resolve_downloader_id(*candidates: str | None) -> str:
    """取第一个指向已配置实例的候选 id；都为空时用默认实例（slots.downloader）。

    指向已删除实例的候选记录告警后跳过，不让一条规则卡住整轮。
    """
    known = downloader_ids()
    for candidate in candidates:
        if not candidate:
            continue
        if candidate in known:
            return candidate
        logger.warning("Downloader instance %r no longer exists; skipped", candidate)
    return settings.plugins.slots.downloader


def _settings_key(d: DownloaderInstance) -> tuple:
    # 带上 Provider 登记项：插件重载后登记项换新，旧客户端随之退役
    entry = plugin_host.get_registry().providers(points.DOWNLOADER).get(d.type)
    return (d.type, d.host, d.username, d.password, d.ssl, entry)


def _reset_client_cache() -> None:
    """Drop the cached/stale concrete clients and refcount state (used by tests)."""
    global _stale_clients, _active_holders, _pending_close
    _client_cache.clear()
    _stale_clients = []
    _active_holders = {}
    _pending_close = set()
    clear_credential_latch()


def clear_credential_latch() -> None:
    """解除所有实例的凭据失败闩锁（配置保存后调用，允许用户重试同值凭据）。"""
    _credential_failed.clear()


async def _close_client(client) -> None:
    try:
        await client.logout()
    except Exception as e:  # pragma: no cover - best-effort cleanup
        logger.debug("Error closing client: %s", e)


async def shutdown() -> None:
    """Log out and close every cached concrete client.

    Invoked by the composition root (`AppContext`) on application shutdown.
    """
    global _stale_clients
    clients = list(_stale_clients) + [c for _, c in _client_cache.values()]
    _client_cache.clear()
    _stale_clients = []
    for client in clients:
        await _close_client(client)


class DownloadClient:
    """Unified async download client.

    Wraps qBittorrent, Aria2, or MockDownloader behind a common interface.
    Intended to be used as an async context manager; authentication is
    performed on ``__aenter__``. The concrete client's session is reused across
    context-manager blocks (see the module-level cache above) and only torn
    down by :func:`shutdown`.
    """

    def __init__(self, instance_id: str | None = None):
        # None：默认实例（slots.downloader）
        self.instance: DownloaderInstance = (
            settings.downloader
            if instance_id is None
            else settings.downloader_instance(instance_id)
        )
        self.instance_id = self.instance.id
        key = _settings_key(self.instance)
        self.client: DownloaderClient
        self._cache_key = key
        cached = _client_cache.get(self.instance_id)
        if cached is not None and cached[0] == key:
            self.client = cached[1]
        else:
            if cached is not None:
                # Settings changed: retire the previous client, close it later.
                # 用列表累积——连续两次改设置（期间没有 enter）不得把第一个
                # 被撤下的客户端顶掉，否则它的连接池泄漏到进程结束。
                _stale_clients.append(cached[1])
            self.client = self.__getClient(self.instance)
            _client_cache[self.instance_id] = (key, self.client)
        self.authed = False

    @staticmethod
    def __getClient(instance: DownloaderInstance) -> DownloaderClient:
        """按实例的 Provider id 从扩展注册表取下载器工厂并实例化。

        内置的 qbittorrent / aria2 / mock 与插件提供的下载器走同一条路径。
        """
        downloader_type = instance.type
        factory = plugin_host.provider(points.DOWNLOADER, downloader_type)
        if factory is None:
            logger.error("Unsupported downloader type: %s", downloader_type)
            raise Exception(f"Unsupported downloader type: {downloader_type}")
        if downloader_type == "mock":
            logger.debug("Using MockDownloader for local development")
        conn = DownloaderConnection(
            host=instance.host,
            username=instance.username,
            password=instance.password,
            ssl=instance.ssl,
        )
        # 只实现 CoreDownloaderClient 的后端（如 aria2 没有 qB 的 RSS 规则）
        # 由 _supports() 按 capabilities 跳过不支持的操作
        return factory(conn)  # type: ignore[no-any-return]

    @property
    def last_auth_error(self) -> str | None:
        """最近一次认证失败的原因（unreachable | credentials | banned）。

        仅 qBittorrent 客户端会区分原因；aria2/mock 无此属性时返回 None。
        """
        return getattr(self.client, "last_auth_error", None)

    def _supports(self, capability: str, op: str) -> bool:
        """Whether the concrete client can perform ``op`` (log once if not)."""
        caps = getattr(self.client, "capabilities", None)
        if caps is not None and getattr(caps, capability, False):
            return True
        key = (type(self.client).__name__, op)
        if key not in _warned_unsupported:
            _warned_unsupported.add(key)
            logger.warning(
                "%s does not support '%s'; skipping.",
                type(self.client).__name__,
                op,
            )
        return False

    async def __aenter__(self):
        if _credential_failed.get(self.instance_id) == self._cache_key:
            # 凭据上次已被服务端明确拒绝且设置未变：不再发 login POST，
            # 避免逐 tick 累积到 qB 的 IP ban。checker/等待循环读的是
            # 具体客户端上的失败原因，这里补齐。
            if hasattr(self.client, "last_auth_error"):
                self.client.last_auth_error = "credentials"  # type: ignore[attr-defined]
            raise ConnectionError(
                "Download client credentials were rejected previously; "
                "update the downloader settings to retry"
            )

        stale_to_close: list[DownloaderClient] = []
        async with _bookkeeping_lock:
            # 先把自己计入引用——auth() 是 await 点，期间一个"设置变更"块
            # 可能进来关闭被撤下的客户端；不先占坑的话，自己正在登录的
            # 客户端会被从脚下抽走。
            _active_holders[id(self.client)] = (
                _active_holders.get(id(self.client), 0) + 1
            )
            while _stale_clients:
                stale = _stale_clients.pop()
                if _active_holders.get(id(stale), 0) > 0:
                    # Still in use by another overlapping block; the last
                    # holder's __aexit__ will close it once released.
                    _pending_close.add(id(stale))
                else:
                    stale_to_close.append(stale)
        for stale in stale_to_close:
            await _close_client(stale)

        if not self.authed:
            # __aexit__ never runs when __aenter__ raises, so every exit path
            # below must release the holder slot itself -- including
            # cancellation mid-login, or the count leaks and a retired client
            # stays pending-close (pool open) forever.
            try:
                await self.auth()
            except BaseException:
                await self._release_holder()
                raise
            if not self.authed:
                if self.last_auth_error == "credentials":
                    _credential_failed[self.instance_id] = self._cache_key
                # Release our slot and close the concrete client's connection
                # pool now or it leaks on every failed connect (#1043) --
                # unless another already-entered block still holds it, in
                # which case defer to its __aexit__ instead of yanking the
                # pool out from under it.
                async with _bookkeeping_lock:
                    cached = _client_cache.get(self.instance_id)
                    if cached is not None and cached[1] is self.client:
                        del _client_cache[self.instance_id]
                    _pending_close.add(id(self.client))
                await self._release_holder()
                raise ConnectionError("Download client authentication failed")

        return self

    async def _release_holder(self) -> None:
        """释放本块对具体客户端的引用；若是最后一个且已标记待关，则关闭。"""
        client = self.client
        to_close = False
        async with _bookkeeping_lock:
            count = _active_holders.get(id(client), 0) - 1
            if count <= 0:
                _active_holders.pop(id(client), None)
                if id(client) in _pending_close:
                    _pending_close.discard(id(client))
                    to_close = True
            else:
                _active_holders[id(client)] = count
        if to_close:
            await _close_client(client)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # The concrete session is reused across operations; do NOT log out
        # here unless this was the last holder of a client that a concurrent
        # block already marked for (deferred) close. Teardown is otherwise
        # deferred to shutdown() (composition root).
        self.authed = False
        await self._release_holder()

    async def auth(self):
        self.authed = await self.client.auth()
        if self.authed:
            logger.debug("Authed.")
        else:
            logger.error("Auth failed.")

    async def set_rss_rule(self, rule_name: str, rule: dict):
        """Create or update a raw qBittorrent RSS auto-download rule."""
        if not self._supports("can_rss_rules", "set_rss_rule"):
            return
        await self.client.rss_set_rule(rule_name=rule_name, rule_def=rule)

    async def get_torrent_info(
        self, category="Bangumi", status_filter="completed", tag=None
    ):
        if not self._supports("can_query", "get_torrent_info"):
            return []
        return await self.client.torrents_info(
            status_filter=status_filter, category=category, tag=tag
        )

    async def get_torrent_files(self, torrent_hash: str):
        if not self._supports("can_query", "get_torrent_files"):
            return []
        return await self.client.torrents_files(torrent_hash=torrent_hash)

    async def torrent_exists(self, torrent_hash: str) -> bool | None:
        """Return task existence, or ``None`` when the backend cannot prove it.

        Destructive recovery paths must distinguish a confirmed absence from
        a transient query failure; an empty bulk snapshot is not sufficient.
        """

        if not self._supports("can_query", "torrent_exists"):
            return None
        return await self.client.torrent_exists(torrent_hash)

    async def rename_torrent_file(
        self, _hash, old_path, new_path, verify: bool = True
    ) -> RenameResult:
        if not self._supports("can_rename", "rename_torrent_file"):
            return RenameResult(
                RenameOutcome.RETRYABLE_FAILURE,
                detail=f"{type(self.client).__name__} does not support file rename",
            )
        raw_result = await self.client.torrents_rename_file(
            torrent_hash=_hash, old_path=old_path, new_path=new_path, verify=verify
        )
        # Compatibility for test doubles and third-party clients that still
        # implement the pre-3.3.4 boolean contract.  Concrete built-in clients
        # all return RenameResult, and the facade always exposes RenameResult.
        if isinstance(raw_result, RenameResult):
            result = raw_result
        else:
            result = RenameResult(
                (
                    RenameOutcome.RENAMED
                    if raw_result
                    else RenameOutcome.RETRYABLE_FAILURE
                ),
                detail=None if raw_result else "legacy downloader returned false",
            )
        if result.succeeded:
            logger.info(f"{old_path} >> {new_path}")
        else:
            logger.debug(
                "Rename %s: %s >> %s",
                result.outcome.value,
                old_path,
                new_path,
            )
        return result

    async def delete_torrent(self, hashes, delete_files: bool = True) -> bool:
        if not self._supports("can_manage", "delete_torrent"):
            return False
        ok = await self.client.torrents_delete(hashes, delete_files=delete_files)
        if ok:
            logger.info("Remove torrents.")
        else:
            logger.error("Failed to remove torrents.")
        return ok

    async def pause_torrent(self, hashes: str):
        if not self._supports("can_manage", "pause_torrent"):
            return
        await self.client.torrents_pause(hashes)

    async def resume_torrent(self, hashes: str):
        if not self._supports("can_manage", "resume_torrent"):
            return
        await self.client.torrents_resume(hashes)

    async def add_torrent(self, torrent: Torrent | list, bangumi: Bangumi) -> AddResult:
        """Download a torrent (or list of torrents) for the given bangumi entry.

        Handles both magnet links and .torrent file URLs, fetching file bytes
        when necessary. Tags each torrent with ``ab:<bangumi_id>`` for later
        episode-offset lookup during rename.

        返回 :class:`AddResult`，区分"新增成功 / 已添加过 / 投递失败"，
        调用方据此决定是否重试或发送失败通知。
        """
        if not bangumi.save_path:
            bangumi.save_path = gen_save_path(bangumi, self.instance.path)
        # 种子行记录实际投递的实例，之后的重命名 / 删除按它路由
        for t in torrent if isinstance(torrent, list) else [torrent]:
            t.downloader_id = self.instance_id
        torrent_url: str | list[str] | None
        async with RequestContent() as req:
            if isinstance(torrent, list):
                if len(torrent) == 0:
                    logger.debug("No torrent found: %s", bangumi.official_title)
                    return AddResult.FAILED
                if "magnet" in torrent[0].url:
                    torrent_url = [t.url for t in torrent]
                    torrent_file = None
                else:
                    torrent_file = await _fetch_torrent_files(req, torrent)
                    if not torrent_file:
                        logger.warning(
                            f"Failed to fetch torrent files for: {bangumi.official_title}"
                        )
                        return AddResult.FAILED
                    torrent_url = None
            else:
                if "magnet" in torrent.url:
                    torrent_url = torrent.url
                    torrent_file = None
                else:
                    torrent_file = await req.get_content(torrent.url)
                    if torrent_file is None:
                        logger.warning(
                            f"Failed to fetch torrent file for: {bangumi.official_title}"
                        )
                        return AddResult.FAILED
                    torrent_url = None
        # Create tag with bangumi_id for offset lookup during rename
        tags = f"ab:{bangumi.id}" if bangumi.id else None
        save_path, category = bangumi.save_path, "Bangumi"
        if plugin_host.hook_runner(points.TORRENT_ADDING) is not None:
            save_path, category, tags = await _apply_adding_hooks(
                torrent, bangumi, save_path, category, tags
            )
        try:
            result = await self.client.add_torrents(
                torrent_urls=torrent_url,
                torrent_files=torrent_file,
                save_path=save_path,
                category=category,
                tags=tags,
            )
            if result is AddResult.ADDED:
                logger.debug("Add torrent: %s", bangumi.official_title)
                return AddResult.ADDED
            if result is AddResult.DUPLICATE:
                logger.debug("Torrent added before: %s", bangumi.official_title)
                return AddResult.DUPLICATE
            return AddResult.FAILED
        except Exception as e:
            logger.error(f"Failed to add torrent for {bangumi.official_title}: {e}")
            return AddResult.FAILED

    async def move_torrent(self, hashes, location):
        if not self._supports("can_manage", "move_torrent"):
            return
        await self.client.move_torrent(hashes=hashes, new_location=location)

    async def set_category(self, hashes, category):
        if not self._supports("can_manage", "set_category"):
            return
        await self.client.set_category(hashes, category)

    async def add_tag(self, torrent_hash: str, tag: str):
        """Add a tag to a torrent."""
        if not self._supports("can_manage", "add_tag"):
            return
        await self.client.add_tag(torrent_hash, tag)
        logger.debug("Added tag '%s' to torrent %s...", tag, torrent_hash[:8])


class DownloaderPool:
    """一次操作内按实例 id 惰性进入 :class:`DownloadClient`，退出时全部释放。

    进入失败的实例在本池内记住、直接抛 ``ConnectionError``，不再重复登录
    （一轮 RSS 可能有很多种子指向同一个不可用实例）。
    """

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._clients: dict[str, DownloadClient] = {}
        self._failed: set[str] = set()

    async def __aenter__(self) -> "DownloaderPool":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._stack.aclose()

    async def get(self, instance_id: str) -> DownloadClient:
        if instance_id in self._failed:
            raise ConnectionError(f"Downloader instance {instance_id} is unavailable")
        if instance_id not in self._clients:
            try:
                self._clients[instance_id] = await self._stack.enter_async_context(
                    DownloadClient(instance_id)
                )
            except Exception as e:
                self._failed.add(instance_id)
                raise ConnectionError(
                    f"Downloader instance {instance_id} is unavailable: {e}"
                ) from e
        return self._clients[instance_id]


async def list_torrents(
    status_filter: str | None = None, timeout: float | None = None
) -> list[dict] | None:
    """所有下载器实例中 Bangumi 分类的种子，每条带 ``downloader_id``。

    不可用（或超过 ``timeout`` 秒）的实例跳过；全部实例都不可用时返回 None。
    """

    async def one(instance_id: str) -> list[dict]:
        async with DownloadClient(instance_id) as client:
            torrents = await client.get_torrent_info(
                category="Bangumi", status_filter=status_filter
            )
        return [{**t, "downloader_id": instance_id} for t in torrents]

    ids = downloader_ids()
    results = await asyncio.gather(
        *(asyncio.wait_for(one(i), timeout) for i in ids), return_exceptions=True
    )
    listed: list[dict] = []
    reachable = False
    for instance_id, result in zip(ids, results):
        if isinstance(result, BaseException):
            logger.debug("Downloader instance %s unavailable: %s", instance_id, result)
            continue
        reachable = True
        listed.extend(result)
    return listed if reachable else None

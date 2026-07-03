import asyncio
import logging

from module.conf import settings
from module.models import Bangumi, Torrent
from module.network import RequestContent

from .base import AddResult, DownloaderClient
from .path import gen_save_path

logger = logging.getLogger(__name__)


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
_client_cache: tuple[tuple, DownloaderClient] | None = None
_stale_client: DownloaderClient | None = None
_active_holders: dict[int, int] = {}
_pending_close: set[int] = set()
_bookkeeping_lock = asyncio.Lock()

# Warn at most once per (client type, operation) when a backend cannot perform
# an operation, so aria2 users are not spammed every rename cycle.
_warned_unsupported: set[tuple[str, str]] = set()


def _settings_key() -> tuple:
    d = settings.downloader
    return (d.type, d.host, d.username, d.password, d.ssl)


def _reset_client_cache() -> None:
    """Drop the cached/stale concrete clients and refcount state (used by tests)."""
    global _client_cache, _stale_client, _active_holders, _pending_close
    _client_cache = None
    _stale_client = None
    _active_holders = {}
    _pending_close = set()


async def _close_client(client) -> None:
    try:
        await client.logout()
    except Exception as e:  # pragma: no cover - best-effort cleanup
        logger.debug("[Downloader] Error closing client: %s", e)


async def shutdown() -> None:
    """Log out and close the cached concrete client.

    Invoked by the composition root (`AppContext`) on application shutdown.
    """
    global _client_cache, _stale_client
    clients = []
    if _stale_client is not None:
        clients.append(_stale_client)
    if _client_cache is not None:
        clients.append(_client_cache[1])
    _client_cache = None
    _stale_client = None
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

    def __init__(self):
        global _client_cache, _stale_client
        key = _settings_key()
        self.client: DownloaderClient
        if _client_cache is not None and _client_cache[0] == key:
            self.client = _client_cache[1]
        else:
            if _client_cache is not None:
                # Settings changed: retire the previous client, close it later.
                _stale_client = _client_cache[1]
            self.client = self.__getClient()
            _client_cache = (key, self.client)
        self.authed = False

    @staticmethod
    def __getClient() -> DownloaderClient:
        """Instantiate the configured downloader client (qbittorrent | aria2 | mock)."""
        downloader_type = settings.downloader.type
        host = settings.downloader.host
        username = settings.downloader.username
        password = settings.downloader.password
        ssl = settings.downloader.ssl
        if downloader_type == "qbittorrent":
            from .client.qb_downloader import QbDownloader

            return QbDownloader(host, username, password, ssl)
        elif downloader_type == "aria2":
            from .client.aria2_downloader import Aria2Downloader

            # Aria2Downloader implements query/rename/manage for real (see its
            # `capabilities`), but has no qB-native RSS-rule/prefs surface
            # (can_rss_rules=False), so it stays structurally narrower than
            # the full `DownloaderClient` protocol -- the facade skips the
            # rss/prefs methods it never calls on this backend.
            return Aria2Downloader(host, username, password)  # type: ignore[return-value]
        elif downloader_type == "mock":
            from .client.mock_downloader import MockDownloader

            logger.debug("[Downloader] Using MockDownloader for local development")
            return MockDownloader()
        else:
            logger.error(
                "[Downloader] Unsupported downloader type: %s", downloader_type
            )
            raise Exception(f"Unsupported downloader type: {downloader_type}")

    def _supports(self, capability: str, op: str) -> bool:
        """Whether the concrete client can perform ``op`` (log once if not)."""
        caps = getattr(self.client, "capabilities", None)
        if caps is not None and getattr(caps, capability, False):
            return True
        key = (type(self.client).__name__, op)
        if key not in _warned_unsupported:
            _warned_unsupported.add(key)
            logger.warning(
                "[Downloader] %s does not support '%s'; skipping.",
                type(self.client).__name__,
                op,
            )
        return False

    async def __aenter__(self):
        global _stale_client, _client_cache
        stale_to_close = None
        async with _bookkeeping_lock:
            if _stale_client is not None:
                if _active_holders.get(id(_stale_client), 0) > 0:
                    # Still in use by another overlapping block; the last
                    # holder's __aexit__ will close it once released.
                    _pending_close.add(id(_stale_client))
                else:
                    stale_to_close = _stale_client
                _stale_client = None
        if stale_to_close is not None:
            await _close_client(stale_to_close)

        if not self.authed:
            await self.auth()
            if not self.authed:
                # __aexit__ never runs when we raise here, so close the
                # concrete client's connection pool now or it leaks on every
                # failed connect (#1043) -- unless another already-entered
                # block still holds it, in which case defer to its
                # __aexit__ instead of yanking the pool out from under it.
                close_now = False
                async with _bookkeeping_lock:
                    if _client_cache is not None and _client_cache[1] is self.client:
                        _client_cache = None
                    if _active_holders.get(id(self.client), 0) > 0:
                        _pending_close.add(id(self.client))
                    else:
                        close_now = True
                if close_now:
                    await _close_client(self.client)
                raise ConnectionError("Download client authentication failed")

        async with _bookkeeping_lock:
            _active_holders[id(self.client)] = (
                _active_holders.get(id(self.client), 0) + 1
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # The concrete session is reused across operations; do NOT log out
        # here unless this was the last holder of a client that a concurrent
        # block already marked for (deferred) close. Teardown is otherwise
        # deferred to shutdown() (composition root).
        self.authed = False
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

    async def auth(self):
        self.authed = await self.client.auth()
        if self.authed:
            logger.debug("[Downloader] Authed.")
        else:
            logger.error("[Downloader] Auth failed.")

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

    async def rename_torrent_file(
        self, _hash, old_path, new_path, verify: bool = True
    ) -> bool:
        if not self._supports("can_rename", "rename_torrent_file"):
            return False
        result = await self.client.torrents_rename_file(
            torrent_hash=_hash, old_path=old_path, new_path=new_path, verify=verify
        )
        if result:
            logger.info(f"{old_path} >> {new_path}")
        else:
            logger.debug("[Downloader] Rename failed: %s >> %s", old_path, new_path)
        return result

    async def delete_torrent(self, hashes, delete_files: bool = True) -> bool:
        if not self._supports("can_manage", "delete_torrent"):
            return False
        ok = await self.client.torrents_delete(hashes, delete_files=delete_files)
        if ok:
            logger.info("[Downloader] Remove torrents.")
        else:
            logger.error("[Downloader] Failed to remove torrents.")
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
            bangumi.save_path = gen_save_path(bangumi)
        torrent_url: str | list[str] | None
        async with RequestContent() as req:
            if isinstance(torrent, list):
                if len(torrent) == 0:
                    logger.debug(
                        "[Downloader] No torrent found: %s", bangumi.official_title
                    )
                    return AddResult.FAILED
                if "magnet" in torrent[0].url:
                    torrent_url = [t.url for t in torrent]
                    torrent_file = None
                else:
                    torrent_file = await asyncio.gather(
                        *[req.get_content(t.url) for t in torrent]
                    )
                    # Filter out None values (failed fetches)
                    torrent_file = [f for f in torrent_file if f is not None]
                    if not torrent_file:
                        logger.warning(
                            f"[Downloader] Failed to fetch torrent files for: {bangumi.official_title}"
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
                            f"[Downloader] Failed to fetch torrent file for: {bangumi.official_title}"
                        )
                        return AddResult.FAILED
                    torrent_url = None
        # Create tag with bangumi_id for offset lookup during rename
        tags = f"ab:{bangumi.id}" if bangumi.id else None
        try:
            result = await self.client.add_torrents(
                torrent_urls=torrent_url,
                torrent_files=torrent_file,
                save_path=bangumi.save_path,
                category="Bangumi",
                tags=tags,
            )
            if result is AddResult.ADDED:
                logger.debug("[Downloader] Add torrent: %s", bangumi.official_title)
                return AddResult.ADDED
            if result is AddResult.DUPLICATE:
                logger.debug(
                    "[Downloader] Torrent added before: %s", bangumi.official_title
                )
                return AddResult.DUPLICATE
            return AddResult.FAILED
        except Exception as e:
            logger.error(
                f"[Downloader] Failed to add torrent for {bangumi.official_title}: {e}"
            )
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
        logger.debug(
            "[Downloader] Added tag '%s' to torrent %s...", tag, torrent_hash[:8]
        )

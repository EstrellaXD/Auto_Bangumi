import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from module.database import Database, engine
from module.downloader import DownloadClient
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent

logger = logging.getLogger(__name__)


class RSSEngine(Database):
    def __init__(self, _engine=engine):
        super().__init__(_engine)
        self._to_refresh = False
        self._filter_cache: dict[str, re.Pattern] = {}

    @staticmethod
    async def _get_torrents(rss: RSSItem) -> list[Torrent]:
        async with RequestContent() as req:
            torrents = await req.get_torrents(rss.url)
            # Add RSS ID
            for torrent in torrents:
                torrent.rss_id = rss.id
        return torrents

    def get_rss_torrents(self, rss_id: int) -> list[Torrent]:
        rss = self.rss.search_id(rss_id)
        if rss:
            return self.torrent.search_rss(rss_id)
        else:
            return []

    async def add_rss(
        self,
        rss_link: str,
        name: str | None = None,
        aggregate: bool = True,
        parser: str = "mikan",
    ):
        if not name:
            async with RequestContent() as req:
                name = await req.get_rss_title(rss_link)
                if not name:
                    return ResponseModel(
                        status=False,
                        status_code=406,
                        msg_en="Failed to get RSS title.",
                        msg_zh="无法获取 RSS 标题。",
                    )
        rss_data = RSSItem(name=name, url=rss_link, aggregate=aggregate, parser=parser)
        if self.rss.add(rss_data):
            return ResponseModel(
                status=True,
                status_code=200,
                msg_en="RSS added successfully.",
                msg_zh="RSS 添加成功。",
            )
        else:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en="RSS added failed.",
                msg_zh="RSS 添加失败。",
            )

    def disable_list(self, rss_id_list: list[int]):
        self.rss.disable_batch(rss_id_list)
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Disable RSS successfully.",
            msg_zh="禁用 RSS 成功。",
        )

    def enable_list(self, rss_id_list: list[int]):
        self.rss.enable_batch(rss_id_list)
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Enable RSS successfully.",
            msg_zh="启用 RSS 成功。",
        )

    def delete_list(self, rss_id_list: list[int]):
        for rss_id in rss_id_list:
            self.rss.delete(rss_id)
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Delete RSS successfully.",
            msg_zh="删除 RSS 成功。",
        )

    async def pull_rss(self, rss_item: RSSItem) -> list[Torrent]:
        torrents = await self._get_torrents(rss_item)
        new_torrents = self.torrent.check_new(torrents)
        return new_torrents

    async def _pull_rss_with_status(
        self, rss_item: RSSItem
    ) -> tuple[list[Torrent], Optional[str]]:
        try:
            torrents = await self.pull_rss(rss_item)
            return torrents, None
        except Exception as e:
            logger.warning(f"[Engine] Failed to fetch RSS {rss_item.name}: {e}")
            return [], str(e)

    def _get_filter_pattern(self, filter_str: str) -> re.Pattern:
        if filter_str not in self._filter_cache:
            raw_pattern = filter_str.replace(",", "|")
            try:
                self._filter_cache[filter_str] = re.compile(
                    raw_pattern, re.IGNORECASE
                )
            except re.error:
                # Filter contains invalid regex chars (e.g. unmatched '[')
                # Fall back to escaping each term for literal matching
                terms = filter_str.split(",")
                escaped = "|".join(re.escape(t) for t in terms)
                self._filter_cache[filter_str] = re.compile(
                    escaped, re.IGNORECASE
                )
                logger.warning(
                    f"[Engine] Filter '{filter_str}' contains invalid regex, "
                    f"using literal matching"
                )
        return self._filter_cache[filter_str]

    def match_torrent(self, torrent: Torrent) -> Optional[Bangumi]:
        matched: Bangumi = self.bangumi.match_torrent(torrent.name)
        if matched:
            if matched.filter == "":
                torrent.bangumi_id = matched.id
                return matched
            pattern = self._get_filter_pattern(matched.filter)
            if not pattern.search(torrent.name):
                torrent.bangumi_id = matched.id
                return matched
        return None

    @staticmethod
    async def _add_torrent_with_compat(
        client: DownloadClient, torrent: Torrent, matched_data: Bangumi
    ) -> str:
        """Add torrent with compatibility fallback.

        Preferred path uses add_torrent_with_status() and expects one of:
        - "added": accepted by downloader
        - "exists": already exists in downloader
        - "failed": add failed

        If the client does not implement that API (or returns unexpected data),
        fallback to legacy add_torrent() bool semantics.
        """
        add_with_status = getattr(client, "add_torrent_with_status", None)
        if callable(add_with_status):
            status = await add_with_status(torrent, matched_data)
            if status in ("added", "exists", "failed"):
                return status
            logger.debug(
                "[Engine] add_torrent_with_status returned unexpected value %r, "
                "falling back to add_torrent().",
                status,
            )

        added = await client.add_torrent(torrent, matched_data)
        return "added" if added else "failed"

    async def refresh_rss(self, client: DownloadClient, rss_id: Optional[int] = None):
        # Get All RSS Items
        if not rss_id:
            rss_items: list[RSSItem] = self.rss.search_active()
        else:
            rss_item = self.rss.search_id(rss_id)
            rss_items = [rss_item] if rss_item else []
        # From RSS Items, fetch all torrents concurrently
        logger.debug("[Engine] Get %s RSS items", len(rss_items))
        results = await asyncio.gather(
            *[self._pull_rss_with_status(rss_item) for rss_item in rss_items]
        )
        now = datetime.now(timezone.utc).isoformat()
        # Process results sequentially (DB operations)
        for rss_item, (new_torrents, error) in zip(rss_items, results):
            # Update connection status
            rss_item.connection_status = "error" if error else "healthy"
            rss_item.last_checked_at = now
            rss_item.last_error = error
            self.add(rss_item)
            torrents_to_persist: list[Torrent] = []
            for torrent in new_torrents:
                matched_data = self.match_torrent(torrent)
                if not matched_data:
                    torrents_to_persist.append(torrent)
                    continue

                add_status = await self._add_torrent_with_compat(
                    client, torrent, matched_data
                )
                if add_status == "added":
                    logger.debug("[Engine] Add torrent %s to client", torrent.name)
                    torrent.downloaded = True
                    torrents_to_persist.append(torrent)
                elif add_status == "exists":
                    logger.debug(
                        "[Engine] Torrent %s already exists in client", torrent.name
                    )
                    torrent.downloaded = True
                    torrents_to_persist.append(torrent)
                else:
                    # Do not persist failed matched torrents.
                    # They should remain "new" and be retried on next refresh.
                    logger.warning(
                        "[Engine] Failed to add matched torrent %s, will retry later.",
                        torrent.name,
                    )
            # Add all torrents to database
            self.torrent.add_all(torrents_to_persist)
        self.commit()

    async def download_bangumi(self, bangumi: Bangumi):
        async with RequestContent() as req:
            torrents = await req.get_torrents(
                bangumi.rss_link, bangumi.filter.replace(",", "|")
            )
            if torrents:
                async with DownloadClient() as client:
                    await client.add_torrent(torrents, bangumi)
                    self.torrent.add_all(torrents)
                    return ResponseModel(
                        status=True,
                        status_code=200,
                        msg_en=f"[Engine] Download {bangumi.official_title} successfully.",
                        msg_zh=f"下载 {bangumi.official_title} 成功。",
                    )
            else:
                return ResponseModel(
                    status=False,
                    status_code=406,
                    msg_en=f"[Engine] Download {bangumi.official_title} failed.",
                    msg_zh=f"[Engine] 下载 {bangumi.official_title} 失败。",
                )

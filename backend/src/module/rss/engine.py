import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from module.database import Database
from module.database.bangumi import match_bangumi_in_list
from module.downloader import DownloadClient
from module.models import Bangumi, ResponseModel, RSSItem, Torrent
from module.network import RequestContent

logger = logging.getLogger(__name__)

# Delay between consecutive requests to the same host. Firing all feeds of one
# site at once gets the whole batch rate-limited with HTTP 429 (#1026).
RSS_PER_HOST_DELAY = 2.0


class RSSEngine:
    def __init__(self, db: Database):
        self.db = db
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

    async def get_rss_torrents(self, rss_id: int) -> list[Torrent]:
        rss = await self.db.rss.search_id(rss_id)
        if rss:
            return await self.db.torrent.search_rss(rss_id)
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
        if await self.db.rss.add(rss_data):
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

    async def disable_list(self, rss_id_list: list[int]):
        await self.db.rss.disable_batch(rss_id_list)
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Disable RSS successfully.",
            msg_zh="禁用 RSS 成功。",
        )

    async def enable_list(self, rss_id_list: list[int]):
        await self.db.rss.enable_batch(rss_id_list)
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Enable RSS successfully.",
            msg_zh="启用 RSS 成功。",
        )

    async def delete_list(self, rss_id_list: list[int]):
        for rss_id in rss_id_list:
            await self.db.rss.delete(rss_id)
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Delete RSS successfully.",
            msg_zh="删除 RSS 成功。",
        )

    async def pull_rss(self, rss_item: RSSItem) -> list[Torrent]:
        torrents = await self._get_torrents(rss_item)
        new_torrents = await self.db.torrent.check_new(torrents)
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
                self._filter_cache[filter_str] = re.compile(raw_pattern, re.IGNORECASE)
            except re.error:
                # Filter contains invalid regex chars (e.g. unmatched '[')
                # Fall back to escaping each term for literal matching
                terms = filter_str.split(",")
                escaped = "|".join(re.escape(t) for t in terms)
                self._filter_cache[filter_str] = re.compile(escaped, re.IGNORECASE)
                logger.warning(
                    f"[Engine] Filter '{filter_str}' contains invalid regex, "
                    f"using literal matching"
                )
        return self._filter_cache[filter_str]

    def match_torrent(
        self, torrent: Torrent, bangumi_list: list[Bangumi]
    ) -> Optional[Bangumi]:
        matched = match_bangumi_in_list(torrent.name, bangumi_list)
        if matched:
            if matched.filter == "":
                return matched
            pattern = self._get_filter_pattern(matched.filter)
            if not pattern.search(torrent.name):
                torrent.bangumi_id = matched.id
                return matched
        return None

    async def refresh_rss(self, client: DownloadClient, rss_id: Optional[int] = None):
        # Get All RSS Items
        if not rss_id:
            rss_items: list[RSSItem] = await self.db.rss.search_active()
        else:
            rss_item = await self.db.rss.search_id(rss_id)
            rss_items = [rss_item] if rss_item else []
        # From RSS Items, fetch all torrents: parallel across hosts, serial
        # (with a delay) within one host so the site never sees a burst (#1026).
        logger.debug("[Engine] Get %s RSS items", len(rss_items))
        semaphore = asyncio.Semaphore(5)

        async def _pull_host_group(items: list[RSSItem]):
            group_results = []
            for i, item in enumerate(items):
                if i and RSS_PER_HOST_DELAY:
                    await asyncio.sleep(RSS_PER_HOST_DELAY)
                async with semaphore:
                    group_results.append(await self._pull_rss_with_status(item))
            return group_results

        host_groups: dict[str, list[RSSItem]] = defaultdict(list)
        for item in rss_items:
            host_groups[urlparse(item.url).netloc].append(item)
        group_lists = list(host_groups.values())
        grouped_results = await asyncio.gather(
            *[_pull_host_group(items) for items in group_lists]
        )
        item_results = [
            (item, result)
            for items, results in zip(group_lists, grouped_results)
            for item, result in zip(items, results)
        ]
        now = datetime.now(timezone.utc).isoformat()
        # Load the active bangumi list once per refresh cycle and match every
        # torrent against it in memory (this is the job the old module-level
        # TTL cache existed to do).
        bangumi_list = await self.db.bangumi.search_all()
        # Process results sequentially (DB operations)
        for rss_item, (new_torrents, error) in item_results:
            # Update connection status
            rss_item.connection_status = "error" if error else "healthy"
            rss_item.last_checked_at = now
            rss_item.last_error = error
            self.db.add(rss_item)
            for torrent in new_torrents:
                matched_data = self.match_torrent(torrent, bangumi_list)
                if matched_data:
                    if await client.add_torrent(torrent, matched_data):
                        logger.debug("[Engine] Add torrent %s to client", torrent.name)
                    torrent.downloaded = True
            # Add all torrents to database
            await self.db.torrent.add_all(new_torrents)
        await self.db.commit()

    async def download_bangumi(self, bangumi: Bangumi):
        async with RequestContent() as req:
            torrents = await req.get_torrents(
                bangumi.rss_link, bangumi.filter.replace(",", "|")
            )
            if torrents:
                async with DownloadClient() as client:
                    await client.add_torrent(torrents, bangumi)
                    await self.db.torrent.add_all(torrents)
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

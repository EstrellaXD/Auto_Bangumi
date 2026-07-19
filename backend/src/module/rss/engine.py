import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from module.conf import settings
from module.database import Database
from module.database.bangumi import _groups_are_similar, match_bangumi_in_list
from module.downloader import AddResult, DownloadClient
from module.models import (
    Bangumi,
    Movie,
    ResponseModel,
    RSSItem,
    RSSPreviewItem,
    RSSPreviewResponse,
    Torrent,
)
from module.network import RequestContent
from module.notification.events import (
    DownloadFailureEvent,
    RssFailureEvent,
    SystemEvent,
)
from module.parser.analyser.selector import (
    parse_configured_release_title,
    parser_engine_snapshot,
)
from module.parser.analyser.tokenizer import (
    MediaType,
    ParsedRelease,
)
from module.parser.release_policy import preference_identity, preference_revision

logger = logging.getLogger(__name__)

# Delay between consecutive requests to the same host. Firing all feeds of one
# site at once gets the whole batch rate-limited with HTTP 429 (#1026).
RSS_PER_HOST_DELAY = 2.0

_PreferenceKey = tuple[int, MediaType, int, int | float]
_PreferenceRank = tuple[int, int]


def _resolution_matches(candidate: str | None, preferred: str | None) -> bool:
    """比较分辨率是否一致（"1080p" 与 "1080" 视为相同）。"""
    if not candidate or not preferred:
        return False
    normalized_candidate = re.sub(r"[pP]$", "", candidate.strip())
    normalized_preferred = re.sub(r"[pP]$", "", preferred.strip())
    return normalized_candidate == normalized_preferred


def _preference_score(release: ParsedRelease, bangumi: Bangumi) -> int:
    """候选版本相对番剧发布组/分辨率偏好的匹配得分：每命中一项 +1。"""
    score = 0
    if bangumi.preferred_group and _groups_are_similar(
        release.group, bangumi.preferred_group
    ):
        score += 1
    if bangumi.preferred_resolution and _resolution_matches(
        release.resolution, bangumi.preferred_resolution
    ):
        score += 1
    return score


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

    async def preview_rss(self, rss_link: str) -> RSSPreviewResponse:
        async with RequestContent() as req:
            torrents = await req.get_torrents(rss_link, _filter="")

        return RSSPreviewResponse(
            items=[
                RSSPreviewItem(
                    name=torrent.name,
                    url=torrent.url,
                    homepage=torrent.homepage,
                )
                for torrent in torrents
            ],
            global_filter=list(settings.rss_parser.filter),
        )

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
            logger.warning(f"Failed to fetch RSS {rss_item.name}: {e}")
            return [], str(e)

    @staticmethod
    def _compile_filter_terms(
        filter_terms: list[str], *, ignore_case: bool
    ) -> re.Pattern:
        terms = [term for term in filter_terms if term]
        if not terms:
            # 如果没有任何过滤条件，返回一个匹配任意字符串的正则表达式
            # 例如，外部使用： _compile_filter_terms(",,,".split(","), ignore_case=True)
            # 等于没有约束，此时返回此正则表达式兜底
            return re.compile(".*")

        flags = re.IGNORECASE if ignore_case else 0
        raw_pattern = "|".join(terms)
        try:
            return re.compile(raw_pattern, flags)
        except re.error:
            escaped = "|".join(re.escape(term) for term in terms)
            logger.warning(
                "Filter %r contains invalid regex, using literal matching",
                raw_pattern,
            )
            return re.compile(escaped, flags)

    def _get_filter_pattern(self, filter_str: str) -> re.Pattern:
        if filter_str not in self._filter_cache:
            pattern = self._compile_filter_terms(
                filter_str.split(","), ignore_case=True
            )
            self._filter_cache[filter_str] = pattern
        return self._filter_cache[filter_str]

    def match_torrent(
        self, torrent: Torrent, bangumi_list: list[Bangumi]
    ) -> Optional[Bangumi]:
        matched = match_bangumi_in_list(torrent.name, bangumi_list)
        if matched:
            # 只有通过排除过滤的种子才关联 bangumi_id：被过滤掉的种子
            # 不能挂在番剧名下，否则 OffsetScanner 会用用户明确排除的
            # 剧集来计算 offset 建议。
            if matched.filter == "":
                torrent.bangumi_id = matched.id
                return matched
            pattern = self._get_filter_pattern(matched.filter)
            if not pattern.search(torrent.name):
                torrent.bangumi_id = matched.id
                return matched
        return None

    @staticmethod
    def _select_preference_skips(
        matched: list[tuple[Torrent, Bangumi]],
        preference_bangumi: dict[int, Bangumi],
        existing_downloaded: dict[int, list[Torrent]],
    ) -> set[int]:
        """按番剧的发布组/分辨率偏好去重：同一集只保留最匹配偏好的版本。

        只影响设置了 ``preferred_group`` 或 ``preferred_resolution`` 的番剧；
        未设置偏好的番剧完全不受影响（沿用旧行为，多字幕组各自下载全部集数）。

        规则：
        - 内容身份包含媒体类型、规范化季度和集数，防止正片、跨季及特典互相
          冲突。
        - 该内容已有下载版本时，新到版本只有偏好得分更高，或偏好得分相同但
          修订号更高时才保留；偏好匹配始终优先于修订号。
        - 同一批次内同一内容出现多个候选时，只保留排序最高的一个。
        - 无法得到安全单集身份的候选不参与去重，始终保留（保守回退，避免因
          解析失败或把 Movie/合集/PV 当成单集而漏下载）。

        返回需要跳过下载的种子对象 id（``id(torrent)``），供调用方在本轮
        ``refresh_rss`` 内部过滤，不做跨请求持久化。
        """
        skip_ids: set[int] = set()

        # 已下载版本：按完整内容身份记录当前最高 (偏好得分, 修订号)。
        existing_best: dict[_PreferenceKey, _PreferenceRank] = {}
        for bangumi_id, torrents in existing_downloaded.items():
            bangumi = preference_bangumi.get(bangumi_id)
            if not bangumi:
                continue
            for torrent in torrents:
                release = parse_configured_release_title(torrent.name)
                if release is None:
                    continue
                identity = preference_identity(release, default_season=bangumi.season)
                if identity is None:
                    continue
                key = (bangumi_id, identity[0], identity[1], identity[2])
                rank = (
                    _preference_score(release, bangumi),
                    preference_revision(release),
                )
                previous = existing_best.get(key)
                if previous is None or rank > previous:
                    existing_best[key] = rank

        # 本批次候选：按 (bangumi_id, media_type, season, episode) 分组。
        batch_groups: dict[_PreferenceKey, list[tuple[Torrent, _PreferenceRank]]] = (
            defaultdict(list)
        )
        for torrent, bangumi in matched:
            if bangumi.id is None or bangumi.id not in preference_bangumi:
                continue
            release = parse_configured_release_title(torrent.name)
            if release is None:
                continue
            identity = preference_identity(release, default_season=bangumi.season)
            if identity is None:
                continue
            key = (bangumi.id, identity[0], identity[1], identity[2])
            rank = (
                _preference_score(release, bangumi),
                preference_revision(release),
            )
            batch_groups[key].append((torrent, rank))

        for key, candidates in batch_groups.items():
            best_rank = max(rank for _, rank in candidates)
            best_torrent = next(t for t, rank in candidates if rank == best_rank)
            prior_best = existing_best.get(key)
            keep_best = prior_best is None or best_rank > prior_best
            for torrent, _rank in candidates:
                if torrent is best_torrent and keep_best:
                    continue
                skip_ids.add(id(torrent))

        return skip_ids

    async def refresh_rss(
        self, client: DownloadClient, rss_id: Optional[int] = None
    ) -> list[SystemEvent]:
        """Refresh feeds with one parser engine for the complete workflow."""
        with parser_engine_snapshot():
            return await self._refresh_rss(client, rss_id)

    async def _refresh_rss(
        self, client: DownloadClient, rss_id: Optional[int] = None
    ) -> list[SystemEvent]:
        # Get All RSS Items
        if not rss_id:
            rss_items: list[RSSItem] = await self.db.rss.search_active()
        else:
            rss_item = await self.db.rss.search_id(rss_id)
            rss_items = [rss_item] if rss_item else []
        # From RSS Items, fetch all torrents: parallel across hosts, serial
        # (with a delay) within one host so the site never sees a burst (#1026).
        logger.debug("Get %s RSS items", len(rss_items))
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
        events: list[SystemEvent] = []

        # Bangumi with a release-group/resolution preference need per-episode
        # dedup; everyone else keeps the old "download every match" behavior.
        preference_bangumi = {
            b.id: b
            for b in bangumi_list
            if b.id is not None and (b.preferred_group or b.preferred_resolution)
        }
        existing_downloaded: dict[int, list[Torrent]] = {}
        if preference_bangumi:
            existing_downloaded = (
                await self.db.torrent.search_downloaded_by_bangumi_ids(
                    list(preference_bangumi)
                )
            )

        # First pass: match every torrent against the bangumi list (this also
        # tags torrent.bangumi_id as a side effect) without downloading yet,
        # so preference dedup can see the whole batch before anything is
        # added to the download client.
        item_matches: list[
            tuple[RSSItem, list[Torrent], Optional[str], list[Optional[Bangumi]]]
        ] = []
        for rss_item, (new_torrents, error) in item_results:
            matches = [self.match_torrent(t, bangumi_list) for t in new_torrents]
            item_matches.append((rss_item, new_torrents, error, matches))

        skip_ids = self._select_preference_skips(
            [
                (torrent, matched)
                for _, new_torrents, _, matches in item_matches
                for torrent, matched in zip(new_torrents, matches)
                if matched is not None
            ],
            preference_bangumi,
            existing_downloaded,
        )

        # Process results sequentially (DB operations)
        for rss_item, new_torrents, error, matches in item_matches:
            # Update connection status. Only notify on the working->error
            # transition (previous_status read before it's overwritten below),
            # not on every tick a feed stays broken.
            previous_status = rss_item.connection_status
            rss_item.connection_status = "error" if error else "healthy"
            rss_item.last_checked_at = now
            rss_item.last_error = error
            self.db.add(rss_item)
            if error and previous_status != "error":
                events.append(
                    RssFailureEvent(
                        rss_name=rss_item.name or rss_item.url,
                        rss_url=rss_item.url,
                        error=error,
                    )
                )
            failed_ids: set[int] = set()
            for torrent, matched_data in zip(new_torrents, matches):
                if matched_data:
                    if id(torrent) in skip_ids:
                        logger.debug(
                            "Skip %s: worse/duplicate release for an "
                            "already-downloaded episode of %s",
                            torrent.name,
                            matched_data.official_title,
                        )
                        continue
                    result = await client.add_torrent(torrent, matched_data)
                    if result is AddResult.FAILED:
                        # 投递失败：不入库（check_new 按 URL 去重，入库就
                        # 永远不会再处理），下一轮 refresh 该种子仍在源里
                        # 时会重新匹配并重试；同时发出失败通知。
                        failed_ids.add(id(torrent))
                        events.append(
                            DownloadFailureEvent(
                                official_title=matched_data.official_title,
                                torrent_name=torrent.name,
                            )
                        )
                    else:
                        # ADDED 与 DUPLICATE（下载器里已有同一种子）都视为
                        # 成功，不再对健康的重复种子发失败通知。
                        logger.debug(
                            "Add torrent %s to client (%s)",
                            torrent.name,
                            result.value,
                        )
                        torrent.downloaded = True
            # Add all torrents to database (投递失败的除外，留待重试)
            to_persist = [t for t in new_torrents if id(t) not in failed_ids]
            if not settings.bangumi_manage.track_orphans:
                # 不记录未匹配种子：它们每轮会被 check_new 重新看到并在内存
                # 中重新匹配（廉价），后补规则能立即接住仍在源里的旧集
                to_persist = [t for t in to_persist if t.bangumi_id is not None]
            await self.db.torrent.add_all(to_persist)
        await self.db.commit()
        return events

    async def download_movie(self, movie: Movie):
        if not movie.rss_link:
            return ResponseModel(
                status=False,
                status_code=406,
                msg_en=f"Download movie {movie.official_title} failed: no RSS link.",
                msg_zh=f"下载剧场版 {movie.official_title} 失败：缺少 RSS 链接。",
            )
        async with RequestContent() as req:
            filter_pattern = movie.filter.replace(",", "|") if movie.filter else ""
            torrents = await req.get_torrents(movie.rss_link, filter_pattern)
            if torrents:
                async with DownloadClient() as client:
                    result = await client.add_torrent(
                        torrents, movie  # type: ignore[arg-type]
                    )
                    if result is AddResult.FAILED:
                        return ResponseModel(
                            status=False,
                            status_code=502,
                            msg_en=f"Download movie {movie.official_title} failed.",
                            msg_zh=f"下载剧场版 {movie.official_title} 失败。",
                        )
                    for torrent in torrents:
                        torrent.downloaded = True
                    await self.db.torrent.add_all(torrents)
                    return ResponseModel(
                        status=True,
                        status_code=200,
                        msg_en=f"Download movie {movie.official_title} successfully.",
                        msg_zh=f"下载剧场版 {movie.official_title} 成功。",
                    )
            else:
                return ResponseModel(
                    status=False,
                    status_code=406,
                    msg_en=f"[Engine] Download movie {movie.official_title} failed.",
                    msg_zh=f"下载剧场版 {movie.official_title} 失败。",
                )

    async def download_bangumi(self, bangumi: Bangumi):
        async with RequestContent() as req:
            torrents = await req.get_torrents(
                bangumi.rss_link, bangumi.filter.replace(",", "|")
            )
            if torrents:
                async with DownloadClient() as client:
                    result = await client.add_torrent(torrents, bangumi)
                    if result is AddResult.FAILED:
                        return ResponseModel(
                            status=False,
                            status_code=502,
                            msg_en=(f"Download {bangumi.official_title} failed."),
                            msg_zh=f"下载 {bangumi.official_title} 失败。",
                        )
                    for torrent in torrents:
                        torrent.downloaded = True
                        # 关联 bangumi_id，避免已匹配的种子被记成孤儿
                        if bangumi.id is not None:
                            torrent.bangumi_id = bangumi.id
                    await self.db.torrent.add_all(torrents)
                    return ResponseModel(
                        status=True,
                        status_code=200,
                        msg_en=f"Download {bangumi.official_title} successfully.",
                        msg_zh=f"下载 {bangumi.official_title} 成功。",
                    )
            else:
                return ResponseModel(
                    status=False,
                    status_code=406,
                    msg_en=f"Download {bangumi.official_title} failed.",
                    msg_zh=f"下载 {bangumi.official_title} 失败。",
                )

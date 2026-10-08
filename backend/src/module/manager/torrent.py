import logging

from module.conf import settings
from module.database import Database
from module.database.bangumi import normalize_save_path
from module.downloader import DownloadClient, downloader_ids, resolve_downloader_id
from module.downloader.path import gen_save_path, save_path_for
from module.downloader.rules import build_rss_rule
from module.models import Bangumi, BangumiUpdate, ResponseModel
from module.parser import TitleParser
from module.parser.analyser.bgm_calendar import fetch_bgm_calendar, match_weekday
from module.parser.analyser.tmdb_parser import tmdb_parser

logger = logging.getLogger(__name__)


def _save_paths(data: Bangumi | BangumiUpdate, root: str) -> set[str]:
    """番剧的种子在某个实例上可能所在的目录：已存的目录（与之前相同），
    以及按该实例下载目录生成的目录（种子投递到了另一个实例）。"""
    paths = {data.save_path, save_path_for(data, root)}
    return {normalize_save_path(p) for p in paths if p}


class TorrentManager:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    async def __match_torrents_list(
        data: Bangumi | BangumiUpdate, instance_id: str | None = None
    ) -> list:
        async with DownloadClient(instance_id) as client:
            torrents = await client.get_torrent_info(status_filter=None)
            targets = _save_paths(data, client.instance.path)
        return [
            torrent.get("hash", torrent.get("infohash_v1", ""))
            for torrent in torrents
            if normalize_save_path(torrent.get("save_path")) in targets
        ]

    async def _torrent_instances(self, data: Bangumi) -> list[str]:
        """番剧的种子所在的下载器实例：种子行记录的实例，加上规则当前的实例。

        规则换过下载器时，旧种子仍在原实例上，删除要逐个实例处理。
        """
        rows = await self.db.torrent.search_by_bangumi_id(data.id)
        ids = {r.downloader_id for r in rows}
        ids.add(resolve_downloader_id(data.downloader_id))
        return sorted(ids & set(downloader_ids()))

    async def delete_torrents(self, data: Bangumi, instance_ids: list[str]):
        found = False
        failed: list[str] = []
        # 逐实例隔离：一个实例不可用或删除失败，其它实例照常清理
        for instance_id in instance_ids:
            try:
                hash_list = await self.__match_torrents_list(data, instance_id)
                if not hash_list:
                    continue
                found = True
                async with DownloadClient(instance_id) as client:
                    deleted = await client.delete_torrent(hash_list)
            except ConnectionError as e:
                logger.warning(
                    "[Manager] Can't delete torrents on %s: %s", instance_id, e
                )
                deleted = False
            if not deleted:
                failed.append(instance_id)
        if failed:
            return ResponseModel(
                status_code=500,
                status=False,
                msg_en=f"Failed to delete torrents for {data.official_title} "
                f"on {', '.join(failed)}",
                msg_zh=f"删除 {data.official_title} 种子失败（{', '.join(failed)}）",
            )
        if found:
            logger.info(f"Delete rule and torrents for {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Delete rule and torrents for {data.official_title}",
                msg_zh=f"删除 {data.official_title} 规则和种子",
            )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find torrents for {data.official_title}",
                msg_zh=f"无法找到 {data.official_title} 的种子",
            )

    async def _disable_orphan_sub_rss(self, data: Bangumi) -> None:
        """停用该番剧独立订阅（aggregate=False）且不再被引用的 RSS 条目（#1053）。

        停用而非删除：无法区分搜索订阅与用户手动添加的独立订阅，删除还会
        连带清掉该 rss_id 下可能属于其他番剧的种子去重记录。聚合订阅由多个
        番剧共享，永不在此处停用；rss_link 可能是逗号拼接的多个链接
        （见 BangumiDatabase.match_list），逐个拆分精确匹配。
        """
        urls = {u.strip() for u in (data.rss_link or "").split(",") if u.strip()}
        if not urls:
            return
        # 含软删除（deleted=True）的番剧：其订阅需保留以便重新启用
        still_referenced: set[str] = set()
        for bangumi in await self.db.bangumi.search_all():
            still_referenced.update(
                u.strip() for u in (bangumi.rss_link or "").split(",") if u.strip()
            )
        orphan_ids: list[int] = []
        for url in urls - still_referenced:
            rss_item = await self.db.rss.search_url(url)
            if rss_item and not rss_item.aggregate and rss_item.enabled:
                orphan_ids.append(rss_item.id)
                logger.info(f"[Manager] Disable orphan RSS feed {url}")
        if orphan_ids:
            await self.db.rss.disable_batch(orphan_ids)

    async def delete_rule(self, _id: int | str, file: bool = False):
        data = await self.db.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            torrent_message = None
            if file:
                # Only the file-cleanup path needs the downloader, so an
                # unreachable downloader shouldn't block a DB-only delete.
                torrent_message = await self.delete_torrents(
                    data, await self._torrent_instances(data)
                )
                if torrent_message.status_code == 500:
                    # 种子行经外键引用番剧，且记录了种子所在的实例：两者都保留，
                    # 实例恢复后重试删除（已删净的实例上匹配不到种子，直接跳过）
                    return ResponseModel(
                        status_code=500,
                        status=False,
                        msg_en=f"Deleting torrents for {data.official_title} "
                        "failed; the rule was kept, retry later.",
                        msg_zh=f"删除 {data.official_title} 的种子失败，"
                        "规则已保留，请稍后重试。",
                    )
            # Clean up torrent records so re-adding the same anime can re-download
            await self.db.torrent.delete_by_bangumi_id(int(_id))
            await self.db.bangumi.delete_one(int(_id))
            # 番剧删除后停用其独立订阅的孤儿 RSS；聚合订阅不受影响
            await self._disable_orphan_sub_rss(data)
            logger.info(f"Delete rule for {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Delete rule for {data.official_title}. {torrent_message.msg_en if file and torrent_message else ''}",
                msg_zh=f"删除 {data.official_title} 规则。{torrent_message.msg_zh if file and torrent_message else ''}",
            )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )

    async def disable_rule(self, _id: str | int, file: bool = False):
        data = await self.db.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            data.deleted = True
            await self.db.bangumi.update(data)
            if file:
                # Only the file-cleanup path needs the downloader, so an
                # unreachable downloader shouldn't block a DB-only disable.
                return await self.delete_torrents(
                    data, await self._torrent_instances(data)
                )
            logger.info(f"Disable rule for {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Disable rule for {data.official_title}",
                msg_zh=f"禁用 {data.official_title} 规则",
            )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )

    async def enable_rule(self, _id: str | int):
        data = await self.db.bangumi.search_id(int(_id))
        if data:
            data.deleted = False
            await self.db.bangumi.update(data)
            logger.info(f"Enable rule for {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Enable rule for {data.official_title}",
                msg_zh=f"启用 {data.official_title} 规则",
            )
        else:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )

    async def update_rule(self, bangumi_id, data: BangumiUpdate):
        old_data = await self.db.bangumi.search_id(bangumi_id)
        if old_data:
            old_instance = resolve_downloader_id(old_data.downloader_id)
            # 部分更新（未带 downloader_id）保持规则原来的实例
            new_instance = resolve_downloader_id(
                data.downloader_id
                if "downloader_id" in data.model_fields_set
                else old_data.downloader_id
            )
            new_path = gen_save_path(
                data, settings.downloader_instance(new_instance).path
            )
            # 换了下载器实例：旧种子留在原实例原位置，之后的新种子进新实例。
            # 没换：规则的种子可能经订阅进了别的实例，逐个实例按各自的
            # 下载目录移动
            if new_instance == old_instance:
                for instance_id in await self._torrent_instances(old_data):
                    root = settings.downloader_instance(instance_id).path
                    moved_path = gen_save_path(data, root)
                    old_paths = _save_paths(old_data, root)
                    if old_paths == {normalize_save_path(moved_path)}:
                        continue
                    match_list = await self.__match_torrents_list(old_data, instance_id)
                    async with DownloadClient(instance_id) as client:
                        # Move existing torrents to new location if path changed
                        if match_list:
                            await client.move_torrent(match_list, moved_path)
                            logger.info(
                                f"Moved torrents from {old_paths} to {moved_path}"
                            )

                        # Update qBittorrent RSS rule if save_path changed。
                        # 只改有这条规则种子的实例或规则自己的实例：setRule
                        # 在别的 qB 上会新建一条启用的自动下载规则
                        if old_data.rule_name and (
                            match_list or instance_id == old_instance
                        ):
                            # Recreate the rule with the new save_path
                            rule = build_rss_rule(data, moved_path)
                            await client.set_rss_rule(old_data.rule_name, rule)
                            logger.info(
                                f"Updated RSS rule {old_data.rule_name} "
                                "with new save_path"
                            )

            data.save_path = new_path
            await self.db.bangumi.update(data, bangumi_id)
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Update rule for {data.official_title}",
                msg_zh=f"更新 {data.official_title} 规则",
            )
        else:
            logger.error(f"Can't find data with {bangumi_id}")
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find data with {bangumi_id}",
                msg_zh=f"无法找到 id {bangumi_id} 的数据",
            )

    async def refresh_poster(self):
        bangumis = await self.db.bangumi.search_all()
        for bangumi in bangumis:
            if not bangumi.poster_link:
                await TitleParser().tmdb_poster_parser(bangumi)
        await self.db.bangumi.update_all(bangumis)
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en="Refresh poster link successfully.",
            msg_zh="刷新海报链接成功。",
        )

    async def refind_poster(self, bangumi_id: int):
        bangumi = await self.db.bangumi.search_id(bangumi_id)
        if not bangumi:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {bangumi_id}",
                msg_zh=f"无法找到 id {bangumi_id}",
            )
        await TitleParser().tmdb_poster_parser(bangumi)
        await self.db.bangumi.update(bangumi)
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en="Refresh poster link successfully.",
            msg_zh="刷新海报链接成功。",
        )

    async def refresh_calendar(self):
        """Fetch Bangumi.tv calendar and update air_weekday for all bangumi."""
        calendar_items = await fetch_bgm_calendar()
        if not calendar_items:
            return ResponseModel(
                status_code=500,
                status=False,
                msg_en="Failed to fetch calendar data from Bangumi.tv.",
                msg_zh="从 Bangumi.tv 获取放送表失败。",
            )
        bangumis = await self.db.bangumi.search_all()
        updated = 0
        for bangumi in bangumis:
            if bangumi.deleted or bangumi.weekday_locked:
                continue
            weekday = match_weekday(
                bangumi.official_title, bangumi.title_raw, calendar_items
            )
            if weekday is not None and weekday != bangumi.air_weekday:
                bangumi.air_weekday = weekday
                updated += 1
        if updated > 0:
            await self.db.bangumi.update_all(bangumis)
        logger.info(f"Calendar refresh: updated {updated} bangumi.")
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Calendar refreshed. Updated {updated} anime.",
            msg_zh=f"放送表已刷新，更新了 {updated} 部番剧。",
        )

    async def search_all_bangumi(self):
        datas = await self.db.bangumi.search_all()
        if not datas:
            return []
        return [data for data in datas if not data.deleted]

    async def search_one(self, _id: int | str):
        data = await self.db.bangumi.search_id(int(_id))
        if not data:
            logger.error(f"Can't find data with {_id}")
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find data with {_id}",
                msg_zh=f"无法找到 id {_id} 的数据",
            )
        else:
            return data

    async def archive_rule(self, _id: int):
        """Archive a bangumi."""
        data = await self.db.bangumi.search_id(_id)
        if not data:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )
        if await self.db.bangumi.archive_one(_id):
            logger.info(f"Archived {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Archived {data.official_title}",
                msg_zh=f"已归档 {data.official_title}",
            )
        return ResponseModel(
            status_code=500,
            status=False,
            msg_en=f"Failed to archive {data.official_title}",
            msg_zh=f"归档 {data.official_title} 失败",
        )

    async def unarchive_rule(self, _id: int):
        """Unarchive a bangumi."""
        data = await self.db.bangumi.search_id(_id)
        if not data:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )
        if await self.db.bangumi.unarchive_one(_id):
            logger.info(f"Unarchived {data.official_title}")
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Unarchived {data.official_title}",
                msg_zh=f"已取消归档 {data.official_title}",
            )
        return ResponseModel(
            status_code=500,
            status=False,
            msg_en=f"Failed to unarchive {data.official_title}",
            msg_zh=f"取消归档 {data.official_title} 失败",
        )

    async def refresh_metadata(self):
        """Refresh TMDB metadata and auto-archive ended series."""
        bangumis = await self.db.bangumi.search_all()
        language = settings.rss_parser.language
        archived_count = 0
        poster_count = 0

        for bangumi in bangumis:
            if bangumi.deleted:
                continue
            tmdb_info = await tmdb_parser(bangumi.official_title, language)
            if tmdb_info:
                # Update poster if missing
                if not bangumi.poster_link and tmdb_info.poster_link:
                    bangumi.poster_link = tmdb_info.poster_link
                    poster_count += 1
                # Auto-archive ended series
                if tmdb_info.series_status == "Ended" and not bangumi.archived:
                    bangumi.archived = True
                    archived_count += 1
                    logger.info(f"Auto-archived ended series: {bangumi.official_title}")

        if archived_count > 0 or poster_count > 0:
            await self.db.bangumi.update_all(bangumis)

        logger.info(
            f"Metadata refresh: archived {archived_count}, updated posters {poster_count}"
        )
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Metadata refreshed. Archived {archived_count} ended series, updated {poster_count} posters.",
            msg_zh=f"已刷新元数据。归档了 {archived_count} 部已完结番剧，更新了 {poster_count} 个海报。",
        )

    async def suggest_offset(self, bangumi_id: int) -> dict:
        """Suggest offset based on TMDB episode counts."""
        data = await self.db.bangumi.search_id(bangumi_id)
        if not data:
            return {
                "suggested_offset": 0,
                "reason": f"Bangumi id {bangumi_id} not found",
            }

        language = settings.rss_parser.language
        tmdb_info = await tmdb_parser(data.official_title, language)

        if not tmdb_info or not tmdb_info.season_episode_counts:
            return {
                "suggested_offset": 0,
                "reason": "Unable to fetch TMDB episode data",
            }

        season = data.season
        if season <= 1:
            return {"suggested_offset": 0, "reason": "Season 1 does not need offset"}

        offset = tmdb_info.get_offset_for_season(season)
        if offset == 0:
            return {"suggested_offset": 0, "reason": "No previous seasons found"}

        # Build reason with episode counts
        prev_seasons = [
            f"S{s}: {tmdb_info.season_episode_counts.get(s, 0)} eps"
            for s in range(1, season)
            if s in tmdb_info.season_episode_counts
        ]
        reason = f"Previous seasons: {', '.join(prev_seasons)}"

        return {"suggested_offset": offset, "reason": reason}

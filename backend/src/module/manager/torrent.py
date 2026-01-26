import logging

from module.conf import settings
from module.database import Database
from module.downloader import DownloadClient
from module.models import Bangumi, BangumiUpdate, ResponseModel
from module.parser import TitleParser
from module.parser.analyser.bgm_calendar import fetch_bgm_calendar, match_weekday
from module.parser.analyser.tmdb_parser import tmdb_parser

logger = logging.getLogger(__name__)


class TorrentManager(Database):
    @staticmethod
    async def __match_torrents_list(data: Bangumi | BangumiUpdate) -> list:
        async with DownloadClient() as client:
            torrents = await client.get_torrent_info(status_filter=None)
        return [
            torrent.get("hash", torrent.get("infohash_v1", ""))
            for torrent in torrents
            if torrent.get("save_path") == data.save_path
        ]

    async def delete_torrents(self, data: Bangumi, client: DownloadClient):
        hash_list = await self.__match_torrents_list(data)
        if hash_list:
            await client.delete_torrent(hash_list)
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

    async def delete_rule(self, _id: int | str, file: bool = False):
        data = self.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            async with DownloadClient() as client:
                self.rss.delete(data.official_title)
                self.bangumi.delete_one(int(_id))
                torrent_message = None
                if file:
                    torrent_message = await self.delete_torrents(data, client)
                logger.info(f"[Manager] Delete rule for {data.official_title}")
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
        data = self.bangumi.search_id(int(_id))
        if isinstance(data, Bangumi):
            async with DownloadClient() as client:
                data.deleted = True
                self.bangumi.update(data)
                if file:
                    torrent_message = await self.delete_torrents(data, client)
                    return torrent_message
                logger.info(f"[Manager] Disable rule for {data.official_title}")
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

    def enable_rule(self, _id: str | int):
        data = self.bangumi.search_id(int(_id))
        if data:
            data.deleted = False
            self.bangumi.update(data)
            logger.info(f"[Manager] Enable rule for {data.official_title}")
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
        old_data: Bangumi = self.bangumi.search_id(bangumi_id)
        if old_data:
            # Move torrent
            match_list = await self.__match_torrents_list(old_data)
            async with DownloadClient() as client:
                new_path = client._gen_save_path(data)
                old_path = old_data.save_path

                # Move existing torrents to new location if path changed
                if match_list and new_path != old_path:
                    await client.move_torrent(match_list, new_path)
                    logger.info(
                        f"[Manager] Moved torrents from {old_path} to {new_path}"
                    )

                # Update qBittorrent RSS rule if save_path changed
                if new_path != old_path and old_data.rule_name:
                    # Recreate the rule with the new save_path
                    rule = {
                        "enable": True,
                        "mustContain": data.title_raw,
                        "mustNotContain": "|".join(data.filter)
                        if isinstance(data.filter, list)
                        else data.filter,
                        "useRegex": True,
                        "episodeFilter": "",
                        "smartFilter": False,
                        "previouslyMatchedEpisodes": [],
                        "affectedFeeds": data.rss_link
                        if isinstance(data.rss_link, str)
                        else ",".join(data.rss_link),
                        "ignoreDays": 0,
                        "lastMatch": "",
                        "addPaused": False,
                        "assignedCategory": "Bangumi",
                        "savePath": new_path,
                    }
                    await client.client.rss_set_rule(
                        rule_name=old_data.rule_name, rule_def=rule
                    )
                    logger.info(
                        f"[Manager] Updated RSS rule {old_data.rule_name} with new save_path"
                    )

            data.save_path = new_path
            self.bangumi.update(data, bangumi_id)
            return ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Update rule for {data.official_title}",
                msg_zh=f"更新 {data.official_title} 规则",
            )
        else:
            logger.error(f"[Manager] Can't find data with {bangumi_id}")
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find data with {bangumi_id}",
                msg_zh=f"无法找到 id {bangumi_id} 的数据",
            )

    async def refresh_poster(self):
        bangumis = self.bangumi.search_all()
        for bangumi in bangumis:
            if not bangumi.poster_link:
                await TitleParser().tmdb_poster_parser(bangumi)
        self.bangumi.update_all(bangumis)
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en="Refresh poster link successfully.",
            msg_zh="刷新海报链接成功。",
        )

    async def refind_poster(self, bangumi_id: int):
        bangumi = self.bangumi.search_id(bangumi_id)
        await TitleParser().tmdb_poster_parser(bangumi)
        self.bangumi.update(bangumi)
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
        bangumis = self.bangumi.search_all()
        updated = 0
        for bangumi in bangumis:
            if bangumi.deleted:
                continue
            weekday = match_weekday(
                bangumi.official_title, bangumi.title_raw, calendar_items
            )
            if weekday is not None and weekday != bangumi.air_weekday:
                bangumi.air_weekday = weekday
                updated += 1
        if updated > 0:
            self.bangumi.update_all(bangumis)
        logger.info(f"[Manager] Calendar refresh: updated {updated} bangumi.")
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Calendar refreshed. Updated {updated} anime.",
            msg_zh=f"放送表已刷新，更新了 {updated} 部番剧。",
        )

    def search_all_bangumi(self):
        datas = self.bangumi.search_all()
        if not datas:
            return []
        return [data for data in datas if not data.deleted]

    def search_one(self, _id: int | str):
        data = self.bangumi.search_id(int(_id))
        if not data:
            logger.error(f"[Manager] Can't find data with {_id}")
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find data with {_id}",
                msg_zh=f"无法找到 id {_id} 的数据",
            )
        else:
            return data

    def archive_rule(self, _id: int):
        """Archive a bangumi."""
        data = self.bangumi.search_id(_id)
        if not data:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )
        if self.bangumi.archive_one(_id):
            logger.info(f"[Manager] Archived {data.official_title}")
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

    def unarchive_rule(self, _id: int):
        """Unarchive a bangumi."""
        data = self.bangumi.search_id(_id)
        if not data:
            return ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )
        if self.bangumi.unarchive_one(_id):
            logger.info(f"[Manager] Unarchived {data.official_title}")
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
        bangumis = self.bangumi.search_all()
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
                    logger.info(
                        f"[Manager] Auto-archived ended series: {bangumi.official_title}"
                    )

        if archived_count > 0 or poster_count > 0:
            self.bangumi.update_all(bangumis)

        logger.info(
            f"[Manager] Metadata refresh: archived {archived_count}, updated posters {poster_count}"
        )
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Metadata refreshed. Archived {archived_count} ended series, updated {poster_count} posters.",
            msg_zh=f"已刷新元数据。归档了 {archived_count} 部已完结番剧，更新了 {poster_count} 个海报。",
        )

    async def suggest_offset(self, bangumi_id: int) -> dict:
        """Suggest offset based on TMDB episode counts."""
        data = self.bangumi.search_id(bangumi_id)
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

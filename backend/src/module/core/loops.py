"""周期任务的单次 tick 逻辑。

每个函数就是原 ``sub_thread.py`` 里循环体的内容，去掉了 ``self`` 依赖，改为
显式参数注入。异常由 :class:`PeriodicTask` 统一捕获，这里不再包裹顶层 try。
"""

import logging

from module.conf import settings
from module.database import Database
from module.downloader import DownloadClient
from module.manager import Renamer, TorrentManager, eps_complete
from module.notification import NotificationManager
from module.rss import RSSAnalyser, RSSEngine

from .offset_scanner import OffsetScanner

logger = logging.getLogger(__name__)


async def rss_tick(analyser: RSSAnalyser) -> None:
    """Analyse aggregate RSS feeds and refresh the RSS engine once."""
    async with DownloadClient() as client:
        with Database() as db:
            engine = RSSEngine(db)
            # Analyse RSS
            rss_list = engine.rss.search_aggregate()
            for rss in rss_list:
                try:
                    await analyser.rss_to_data(rss, engine)
                except Exception:
                    # RSS 可能在遍历期间被 API 删除，跳过即可
                    logger.debug(
                        "[RSSThread] Skipping RSS id=%s, likely deleted",
                        rss.id if hasattr(rss, "id") else "?",
                    )
            # Run RSS Engine
            await engine.refresh_rss(client)
    if settings.bangumi_manage.eps_complete:
        await eps_complete()


async def rename_tick(notifier: NotificationManager) -> None:
    """Rename completed downloads and notify via the shared notifier."""
    async with DownloadClient() as client:
        renamer = Renamer(client)
        renamed_info = await renamer.rename()
    if settings.notification.enable and renamed_info:
        for info in renamed_info:
            await notifier.send_all(info)


async def offset_scan_tick() -> None:
    """Scan all bangumi for season/episode offset mismatches."""
    scanner = OffsetScanner()
    flagged = await scanner.scan_all()
    logger.info("[OffsetScanThread] Scan complete, flagged %s bangumi", flagged)


async def calendar_tick() -> None:
    """Refresh bangumi calendar metadata."""
    with Database() as db:
        manager = TorrentManager(db)
        resp = await manager.refresh_calendar()
        if resp.status:
            logger.info("[CalendarRefreshThread] Calendar refresh completed")
        else:
            logger.warning(
                "[CalendarRefreshThread] Calendar refresh failed: %s", resp.msg_en
            )

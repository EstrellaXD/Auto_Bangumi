"""周期任务的单次 tick 逻辑。

每个函数就是原 ``sub_thread.py`` 里循环体的内容，去掉了 ``self`` 依赖，改为
显式参数注入。异常由 :class:`PeriodicTask` 统一捕获，这里不再包裹顶层 try。
"""

import asyncio
import logging

from module.conf import settings
from module.database import Database
from module.downloader import DownloadClient
from module.manager import Renamer, TorrentManager, eps_complete
from module.notification import NotificationManager, UpdateAvailableEvent
from module.rss import RSSAnalyser, RSSEngine
from module.update import updater

from .offset_scanner import OffsetScanner

logger = logging.getLogger(__name__)


async def rss_tick(analyser: RSSAnalyser, notifier: NotificationManager) -> None:
    """Analyse aggregate RSS feeds and refresh the RSS engine once."""
    async with DownloadClient() as client:
        async with Database() as db:
            engine = RSSEngine(db)
            # Analyse RSS
            rss_list = await db.rss.search_aggregate()
            for rss in rss_list:
                try:
                    await analyser.rss_to_data(rss, engine)
                except Exception:
                    # 仅当该 RSS 确实已在遍历期间被 API 删除时才视为预期情况；
                    # 其余异常可能是真实 bug，需在 WARNING 级别带完整堆栈。
                    if await db.rss.search_id(rss.id) is None:
                        logger.debug(
                            "Skipping RSS id=%s, deleted during iteration",
                            rss.id,
                        )
                    else:
                        logger.warning(
                            "Error analysing RSS id=%s (%s)",
                            rss.id,
                            rss.url,
                            exc_info=True,
                        )
            # Run RSS Engine
            events = await engine.refresh_rss(client)
    if events:
        # 站内通知中心要求事件总是送达 notifier（send_event 内部先落库，
        # 再按 settings.notification.enable 决定是否外发）。
        # One provider's exception never blocks another event (send_event
        # itself gathers across providers); gathering across events too
        # means a tick with several RSS failures doesn't serialize their
        # notification latency (#1026 fallout: many feeds can fail in the
        # same tick when a whole host is unreachable).
        await asyncio.gather(*[notifier.send_event(e) for e in events])
    if settings.bangumi_manage.eps_complete:
        await eps_complete()


async def rename_tick(notifier: NotificationManager) -> None:
    """Rename completed downloads and notify via the shared notifier."""
    async with DownloadClient() as client:
        renamer = Renamer(client)
        renamed_info = await renamer.rename()
    if settings.notification.enable and renamed_info:
        # Gather across renamed items so a batch rename (e.g. first import of
        # a season) doesn't serialize N notification round-trips.
        await asyncio.gather(*[notifier.send_all(info) for info in renamed_info])


async def offset_scan_tick(notifier: NotificationManager) -> None:
    """Scan all bangumi for season/episode offset mismatches."""
    # 扫描结果由 OffsetScanner.scan_all 自己记录，这里不再重复记一行
    scanner = OffsetScanner()
    events = await scanner.scan_all()
    if events:
        await asyncio.gather(*[notifier.send_event(e) for e in events])


async def update_check_tick(notifier: NotificationManager) -> None:
    """每日检查一次 GitHub Release，发现新版本时写入通知中心。

    ``UpdateAvailableEvent.once=True``（按最新版本号去重），同一版本终生只
    提醒一次；检查失败（网络/限流）静默跳过，避免每天误报。
    """
    result = await updater.check_update(settings.update.channel, force=False)
    if result.error:
        logger.debug("Update check failed: %s", result.error)
        return
    if not result.has_update:
        return
    await notifier.send_event(
        UpdateAvailableEvent(
            current=result.current,
            latest=result.latest or "",
            channel=result.channel,
            notes=result.notes or "",
        )
    )


async def calendar_tick() -> None:
    """Refresh bangumi calendar metadata."""
    async with Database() as db:
        manager = TorrentManager(db)
        resp = await manager.refresh_calendar()
        # 成功已由 TorrentManager.refresh_calendar 记录（含更新数量）
        if not resp.status:
            logger.warning("Calendar refresh failed: %s", resp.msg_en)

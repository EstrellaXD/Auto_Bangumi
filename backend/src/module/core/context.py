"""应用组合根（composition root）。

``AppContext`` 取代原先的 ``Program`` 上帝对象：由 ``create_app`` 构造、由
lifespan 拥有其生命周期。它持有 settings、通知管理器、调度器，以及下载器状态的
TTL 缓存，并负责启动迁移、后台任务的启停与配置热重载。
"""

import asyncio
import logging
import time

from module.checker import Checker
from module.conf import LEGACY_DATA_PATH, VERSION, settings
from module.database import Database
from module.downloader.download_client import shutdown as downloader_shutdown
from module.models import ResponseModel
from module.network.request_url import reset_shared_client
from module.notification import DownloaderUnavailableEvent, NotificationManager
from module.parser.analyser.mikan_parser import reset_cache as reset_mikan_cache
from module.parser.analyser.tmdb_parser import reset_cache as reset_tmdb_cache
from module.parser.title_parser import reset_cache as reset_llm_parser
from module.rss import RSSAnalyser
from module.searcher.searcher import reset_cache as reset_poster_cache
from module.update import (
    cache_image,
    data_migration,
    first_run,
    from_30_to_31,
    from_31_to_32,
    run_migrations,
)

from .loops import (
    calendar_tick,
    offset_scan_tick,
    rename_tick,
    rss_tick,
    update_check_tick,
)
from .scheduler import PeriodicTask, Scheduler

logger = logging.getLogger(__name__)

# Downloader-status cache TTL, in seconds (moved from the old ProgramStatus).
DOWNLOADER_STATUS_TTL = 60

# Background loop cadence (seconds).
OFFSET_SCAN_INTERVAL = 6 * 60 * 60
CALENDAR_REFRESH_INTERVAL = 24 * 60 * 60
UPDATE_CHECK_INTERVAL = 24 * 60 * 60
OFFSET_SCAN_INITIAL_DELAY = 60
CALENDAR_INITIAL_DELAY = 120
UPDATE_CHECK_INITIAL_DELAY = 300

# Downloader wait-retry loop on startup.
_DOWNLOADER_MAX_RETRIES = 10
_DOWNLOADER_RETRY_INTERVAL = 30

figlet = r"""
               _        ____                                    _
    /\        | |      |  _ \                                  (_)
   /  \  _   _| |_ ___ | |_) | __ _ _ __   __ _ _   _ _ __ ___  _
  / /\ \| | | | __/ _ \|  _ < / _` | '_ \ / _` | | | | '_ ` _ \| |
 / ____ \ |_| | || (_) | |_) | (_| | | | | (_| | |_| | | | | | | |
/_/    \_\__,_|\__\___/|____/ \__,_|_| |_|\__, |\__,_|_| |_| |_|_|
                                           __/ |
                                          |___/
"""


class AppContext:
    """Owns application-wide state and orchestrates startup/shutdown/reload."""

    def __init__(
        self,
        settings_obj,
        notifier: NotificationManager,
        scheduler: Scheduler,
        analyser: RSSAnalyser,
    ) -> None:
        self.settings = settings_obj
        self.notifier = notifier
        self.scheduler = scheduler
        self.analyser = analyser
        # Downloader-status TTL cache (was ProgramStatus.check_downloader_status).
        self._downloader_status = False
        self._downloader_reason: str | None = None
        self._downloader_last_check: float = 0.0
        self._startup_done = False
        self._lifecycle_lock = asyncio.Lock()
        # The background task spawned by start_tasks() (downloader-wait +
        # scheduler start). Tracked so stop() can cancel it if shutdown
        # happens while it is still waiting on the downloader.
        self._start_task: asyncio.Task | None = None
        # True when this boot created the database (genuine first run); the
        # lifespan then skips auto-starting background tasks, matching the old
        # Program.startup() early-return.
        self.first_run_boot = False

    # ------------------------------------------------------------------ build

    @classmethod
    def build(cls, settings_obj) -> "AppContext":
        """Pure wiring: construct the object graph, perform no I/O.

        The scheduler closures capture ``notifier`` / ``analyser`` directly.
        ``NotificationManager.rebuild()`` mutates in place, so a config reload is
        reflected without re-wiring the tasks; ``interval`` reads settings live.
        """
        analyser = RSSAnalyser()
        notifier = NotificationManager()
        scheduler = Scheduler(
            [
                PeriodicTask(
                    name="rss",
                    run=lambda: rss_tick(analyser, notifier),
                    interval=lambda: settings_obj.program.rss_time,
                    enabled=Checker.check_analyser,
                ),
                PeriodicTask(
                    name="rename",
                    run=lambda: rename_tick(notifier),
                    interval=lambda: settings_obj.program.rename_time,
                    enabled=Checker.check_renamer,
                ),
                PeriodicTask(
                    name="offset_scan",
                    run=lambda: offset_scan_tick(notifier),
                    interval=lambda: OFFSET_SCAN_INTERVAL,
                    initial_delay=OFFSET_SCAN_INITIAL_DELAY,
                ),
                PeriodicTask(
                    name="calendar",
                    run=calendar_tick,
                    interval=lambda: CALENDAR_REFRESH_INTERVAL,
                    initial_delay=CALENDAR_INITIAL_DELAY,
                ),
                PeriodicTask(
                    name="update_check",
                    run=lambda: update_check_tick(notifier),
                    interval=lambda: UPDATE_CHECK_INTERVAL,
                    initial_delay=UPDATE_CHECK_INITIAL_DELAY,
                    enabled=lambda: settings_obj.update.auto_check,
                ),
            ]
        )
        return cls(settings_obj, notifier, scheduler, analyser)

    # ------------------------------------------------------------------ status

    @property
    def is_running(self) -> bool:
        if Checker.check_first_run():
            return False
        start_pending = self._start_task is not None and not self._start_task.done()
        return self.scheduler.running or start_pending

    @property
    def first_run(self) -> bool:
        return Checker.check_first_run()

    async def check_downloader(self) -> bool:
        """Raw downloader reachability check (no cache), used by /check/downloader."""
        return await Checker.check_downloader()

    async def check_downloader_status(self) -> bool:
        """TTL-cached downloader reachability, used by the startup wait loop."""
        now = time.monotonic()
        if (
            not self._downloader_status
            or (now - self._downloader_last_check) >= DOWNLOADER_STATUS_TTL
        ):
            (
                self._downloader_status,
                self._downloader_reason,
            ) = await Checker.check_downloader_detail()
            self._downloader_last_check = now
        return self._downloader_status

    # ------------------------------------------------------------------ startup

    @staticmethod
    def _start_info() -> None:
        for line in figlet.splitlines():
            logger.info(line.strip("\n"))
        logger.info(
            f"Version {VERSION}  Author: EstrellaXD Twitter: https://twitter.com/Estrella_Pan"
        )
        logger.info("GitHub: https://github.com/EstrellaXD/Auto_Bangumi/")
        logger.info("Starting AutoBangumi...")

    async def startup(self) -> None:
        """Run first-run detection and database migrations.

        Awaited from the lifespan *before* serving requests, so any failure
        aborts boot loudly instead of being swallowed. Does not start tasks.
        """
        if self._startup_done:
            return
        self._start_info()
        if not Checker.check_database():
            await first_run()
            logger.info("No db file exists, create database file.")
            self.first_run_boot = True
            self._startup_done = True
            return
        if LEGACY_DATA_PATH.exists():
            logger.info(
                "Legacy data detected, starting data migration, please wait patiently."
            )
            # data_migration() writes into the bangumi/rssitem tables directly,
            # so the schema must exist and be up to date first.
            async with Database() as db:
                await db.create_table()
                await db.run_migrations()
            await data_migration()
        else:
            is_same, last_minor = Checker.check_version()
            if not is_same:
                if last_minor is not None and last_minor == 0:
                    await from_30_to_31()
                    logger.info("Database migrated from 3.0 to 3.1.")
                await from_31_to_32()
                logger.info("Database updated.")
            else:
                # Always check schema version and run pending migrations,
                # in case a previous migration was interrupted or failed.
                await run_migrations()
        if not Checker.check_img_cache():
            logger.info("No image cache exists, create image cache.")
            await cache_image()
        self._startup_done = True

    # ------------------------------------------------------------------ tasks

    async def _wait_for_downloader(self) -> None:
        retry_count = 0
        while not await self.check_downloader_status():
            reason = self._downloader_reason or "unreachable"
            if reason in ("credentials", "banned"):
                # 凭据错误/IP 被封时等待没有意义，继续探测反而会累积失败
                # 登录、触发（或加剧）qB 的 WebUI IP ban——立即放弃并通知。
                logger.error(
                    "Downloader rejected authentication (%s); giving up. "
                    "Program will continue but download functions will not work.",
                    reason,
                )
                await self._notify_downloader_unavailable(reason)
                return
            retry_count += 1
            logger.warning(
                f"Downloader is not running. (attempt {retry_count}/{_DOWNLOADER_MAX_RETRIES})"
            )
            if retry_count >= _DOWNLOADER_MAX_RETRIES:
                logger.error(
                    "Failed to connect to downloader after maximum retries. "
                    "Please check downloader settings and network/proxy configuration. "
                    "Program will continue but download functions will not work."
                )
                await self._notify_downloader_unavailable("unreachable")
                break
            logger.info("Waiting for downloader to start...")
            await asyncio.sleep(_DOWNLOADER_RETRY_INTERVAL)

    async def _notify_downloader_unavailable(self, reason: str) -> None:
        try:
            await self.notifier.send_event(
                DownloaderUnavailableEvent(
                    host=self.settings.downloader.host, reason=reason
                )
            )
        except Exception:
            logger.warning(
                "Failed to emit downloader-unavailable notification", exc_info=True
            )

    async def _run_start_tasks(self) -> None:
        """Body of the background start task: wait for the downloader, then start loops."""
        await self._wait_for_downloader()
        async with self._lifecycle_lock:
            if not Checker.check_first_run() and not self.scheduler.running:
                self.scheduler.start_all()
        logger.info("Program running.")

    @staticmethod
    def _supervise_start_task(task: asyncio.Task) -> None:
        """Log-and-surface any exception from the background start task."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("Background start task failed", exc_info=exc)

    async def start_tasks(self) -> ResponseModel:
        """Kick off the downloader-wait + loop-start in the background and return immediately.

        The downloader wait-retry loop can take up to ~300s (CONTRACT #5); running
        it inline used to block both the lifespan and the /start,/restart API
        handlers for that long. It now runs as a supervised background task
        tracked on ``self._start_task`` so ``stop()`` can cancel it cleanly.

        Reloads settings through ``reload_settings()`` (the single reload entry
        point) rather than calling ``settings.load()`` directly; the scheduler
        is not yet running at this point so its restart branch is a no-op.
        """
        async with self._lifecycle_lock:
            return await self._start_tasks_unlocked()

    async def _start_tasks_unlocked(self) -> ResponseModel:
        await self._reload_settings_unlocked()
        if not self.scheduler.running and (
            self._start_task is None or self._start_task.done()
        ):
            self._start_task = asyncio.create_task(self._run_start_tasks())
            self._start_task.add_done_callback(self._supervise_start_task)
        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Program starting.",
            msg_zh="程序启动中。",
        )

    async def stop(self) -> ResponseModel:
        """Cancel any pending start task, stop background loops, and close the cached downloader session."""
        async with self._lifecycle_lock:
            return await self._stop_unlocked()

    async def _stop_unlocked(self) -> ResponseModel:
        was_running = self.is_running
        if self._start_task is not None:
            self._start_task.cancel()
            try:
                await self._start_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning(f"Background start task failed during shutdown: {e}")
            self._start_task = None
        if self.scheduler.running:
            await self.scheduler.stop_all()
        if was_running:
            resp = ResponseModel(
                status=True,
                status_code=200,
                msg_en="Program stopped.",
                msg_zh="程序停止成功。",
            )
        else:
            resp = ResponseModel(
                status=False,
                status_code=406,
                msg_en="Program is not running.",
                msg_zh="程序未运行。",
            )
        # Always release the shared qB session; shutdown() is idempotent and the
        # session is lazily rebuilt on the next DownloadClient() use.
        await downloader_shutdown()
        return resp

    async def restart(self) -> ResponseModel:
        async with self._lifecycle_lock:
            return await self._restart_unlocked()

    async def _restart_unlocked(self) -> ResponseModel:
        stop_ok = True
        try:
            await self._stop_unlocked()
        except Exception as e:
            logger.warning(f"Error during stop in restart: {e}")
            stop_ok = False
        start_ok = True
        try:
            await self._start_tasks_unlocked()
        except Exception as e:
            logger.error(f"Error during start in restart: {e}")
            start_ok = False
        if start_ok and stop_ok:
            return ResponseModel(
                status=True,
                status_code=200,
                msg_en="Program restarted.",
                msg_zh="程序重启成功。",
            )
        elif start_ok:
            return ResponseModel(
                status=True,
                status_code=200,
                msg_en="Program restarted (stop had warnings).",
                msg_zh="程序重启成功（停止时有警告）。",
            )
        else:
            return ResponseModel(
                status=False,
                status_code=500,
                msg_en="Program failed to restart.",
                msg_zh="程序重启失败。",
            )

    # ------------------------------------------------------------------ reload

    async def reload_settings(self) -> None:
        """Single choreography for a config update: reload + re-apply live state.

        This is the ONLY place settings are reloaded from disk — callers must
        route through here (not a bare ``settings.load()``) so the HTTP
        client, notifier, endpoint-keyed caches, and scheduler all stay in
        sync with the new config.
        """
        async with self._lifecycle_lock:
            await self._reload_settings_unlocked()

    async def _reload_settings_unlocked(self) -> None:
        # settings.load() does synchronous file I/O; keep it off the event loop.
        await asyncio.to_thread(settings.load)
        await reset_shared_client()
        # Endpoint-keyed caches (TMDB/Mikan/poster lookups, the LLM parser
        # singleton) must be dropped too, or a changed tmdb_base_url/bgm_base_url
        # keeps serving results cached from the old endpoint.
        reset_tmdb_cache()
        reset_mikan_cache()
        reset_poster_cache()
        reset_llm_parser()
        self.notifier.rebuild()
        if self.scheduler.running:
            await self.scheduler.stop_all()
            self.scheduler.start_all()

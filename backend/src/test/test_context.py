"""Tests for module.core.context.AppContext."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.conf import settings as real_settings
from module.core.context import AppContext
from module.models import ResponseModel


@pytest.fixture
def ctx():
    """A built AppContext whose notifier/scheduler are replaced with mocks."""
    ctx = AppContext.build(real_settings)
    ctx.notifier = MagicMock()
    ctx.scheduler = MagicMock()
    ctx.scheduler.stop_all = AsyncMock()
    ctx.scheduler.start_all = MagicMock()
    # A freshly built context has not started its scheduler yet; set this
    # explicitly since a bare MagicMock attribute is truthy by default and
    # would make reload_settings() think a restart is needed.
    ctx.scheduler.running = False

    def _mark_running():
        ctx.scheduler.running = True

    async def _mark_stopped():
        ctx.scheduler.running = False

    ctx.scheduler.start_all.side_effect = _mark_running
    ctx.scheduler.stop_all.side_effect = _mark_stopped
    return ctx


# ---------------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------------


class TestBuild:
    def test_build_registers_four_named_tasks(self):
        built = AppContext.build(real_settings)
        names = [t.name for t in built.scheduler.tasks]
        assert names == ["rss", "rename", "offset_scan", "calendar"]

    def test_build_does_no_io(self):
        """build() is pure wiring: not running, startup not done."""
        built = AppContext.build(real_settings)
        assert built.is_running is False
        assert built._startup_done is False
        assert built.first_run_boot is False


# ---------------------------------------------------------------------------
# startup()
# ---------------------------------------------------------------------------


class TestStartup:
    async def test_first_run_creates_db_and_flags_boot(self, ctx):
        """No database => first_run() runs, boot is flagged, tasks not started."""
        with (
            patch("module.core.context.Checker.check_database", return_value=False),
            patch("module.core.context.first_run") as mock_first_run,
        ):
            await ctx.startup()

        mock_first_run.assert_called_once()
        assert ctx.first_run_boot is True
        assert ctx._startup_done is True
        assert ctx.scheduler.running is False

    async def test_existing_db_runs_pending_migrations(self, ctx):
        """Existing DB, same version => run_migrations() is invoked."""
        with (
            patch("module.core.context.Checker.check_database", return_value=True),
            patch("module.core.context.LEGACY_DATA_PATH") as legacy,
            patch(
                "module.core.context.Checker.check_version",
                return_value=(True, None),
            ),
            patch("module.core.context.Checker.check_img_cache", return_value=True),
            patch("module.core.context.run_migrations") as mock_run,
        ):
            legacy.exists.return_value = False
            await ctx.startup()

        mock_run.assert_called_once()
        assert ctx.first_run_boot is False
        assert ctx._startup_done is True

    async def test_version_bump_runs_cross_version_migrations(self, ctx):
        """A version change from minor 0 triggers 3.0->3.1 then 3.1->3.2."""
        with (
            patch("module.core.context.Checker.check_database", return_value=True),
            patch("module.core.context.LEGACY_DATA_PATH") as legacy,
            patch(
                "module.core.context.Checker.check_version",
                return_value=(False, 0),
            ),
            patch("module.core.context.Checker.check_img_cache", return_value=True),
            patch("module.core.context.from_30_to_31", new=AsyncMock()) as m_30_31,
            patch("module.core.context.from_31_to_32", new=AsyncMock()) as m_31_32,
        ):
            legacy.exists.return_value = False
            await ctx.startup()

        m_30_31.assert_awaited_once()
        m_31_32.assert_awaited_once()

    async def test_startup_is_idempotent(self, ctx):
        """A second startup() call returns immediately without re-running."""
        ctx._startup_done = True
        with patch("module.core.context.Checker.check_database") as check_db:
            await ctx.startup()
        check_db.assert_not_called()


# ---------------------------------------------------------------------------
# start_tasks()
# ---------------------------------------------------------------------------


class TestStartTasks:
    async def test_start_tasks_waits_then_starts_scheduler(self, ctx):
        with (
            patch("module.core.context.settings"),
            patch("module.core.context.reset_shared_client", new=AsyncMock()),
            patch("module.core.context.Checker.check_first_run", return_value=False),
            patch(
                "module.core.context.Checker.check_downloader",
                new=AsyncMock(return_value=True),
            ),
        ):
            resp = await ctx.start_tasks()
            # start_tasks() only kicks off the downloader-wait + scheduler-start
            # as a supervised background task and returns immediately; await it
            # here so the assertions below observe its effects.
            await ctx._start_task
            assert ctx.is_running is True

        ctx.scheduler.start_all.assert_called_once()
        assert isinstance(resp, ResponseModel)
        assert resp.status is True

    async def test_start_tasks_runs_reload_choreography(self, ctx):
        """start_tasks() must use the same reload choreography as config updates."""
        with (
            patch("module.core.context.settings") as mock_settings,
            patch("module.core.context.reset_shared_client", new=AsyncMock()),
            patch("module.core.context.Checker.check_first_run", return_value=False),
            patch(
                "module.core.context.Checker.check_downloader",
                new=AsyncMock(return_value=True),
            ),
        ):
            await ctx.start_tasks()
            await ctx._start_task

        mock_settings.load.assert_called_once()

    async def test_concurrent_start_tasks_create_one_background_start(self, ctx):
        start_gate = asyncio.Event()

        async def check_downloader():
            await start_gate.wait()
            return True

        with (
            patch("module.core.context.settings"),
            patch("module.core.context.reset_shared_client", new=AsyncMock()),
            patch("module.core.context.Checker.check_first_run", return_value=False),
            patch(
                "module.core.context.Checker.check_downloader",
                new=AsyncMock(side_effect=check_downloader),
            ),
        ):
            await asyncio.gather(ctx.start_tasks(), ctx.start_tasks())
            start_gate.set()
            await ctx._start_task

        ctx.scheduler.start_all.assert_called_once()


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------


class TestStop:
    async def test_stop_running_stops_scheduler_and_downloader(self, ctx):
        ctx.scheduler.running = True
        with (
            patch("module.core.context.Checker.check_first_run", return_value=False),
            patch(
                "module.core.context.downloader_shutdown", new=AsyncMock()
            ) as mock_shutdown,
        ):
            resp = await ctx.stop()

        ctx.scheduler.stop_all.assert_awaited_once()
        mock_shutdown.assert_awaited_once()
        assert ctx.scheduler.running is False
        assert resp.status_code == 200

    async def test_stop_not_running_still_closes_downloader(self, ctx):
        ctx.scheduler.running = False
        with (
            patch("module.core.context.Checker.check_first_run", return_value=False),
            patch(
                "module.core.context.downloader_shutdown", new=AsyncMock()
            ) as mock_shutdown,
        ):
            resp = await ctx.stop()

        ctx.scheduler.stop_all.assert_not_awaited()
        mock_shutdown.assert_awaited_once()
        assert resp.status_code == 406


# ---------------------------------------------------------------------------
# reload_settings()
# ---------------------------------------------------------------------------


class TestReloadSettings:
    async def test_reload_runs_full_choreography_when_running(self, ctx):
        ctx.scheduler.running = True
        with (
            patch("module.core.context.settings") as mock_settings,
            patch(
                "module.core.context.reset_shared_client", new=AsyncMock()
            ) as mock_reset,
        ):
            await ctx.reload_settings()

        mock_settings.load.assert_called_once()
        mock_reset.assert_awaited_once()
        ctx.notifier.rebuild.assert_called_once()
        ctx.scheduler.stop_all.assert_awaited_once()
        ctx.scheduler.start_all.assert_called_once()

    async def test_reload_skips_scheduler_restart_when_idle(self, ctx):
        ctx.scheduler.running = False
        with (
            patch("module.core.context.settings") as mock_settings,
            patch("module.core.context.reset_shared_client", new=AsyncMock()),
        ):
            await ctx.reload_settings()

        mock_settings.load.assert_called_once()
        ctx.notifier.rebuild.assert_called_once()
        ctx.scheduler.stop_all.assert_not_awaited()
        ctx.scheduler.start_all.assert_not_called()

    async def test_reload_resets_endpoint_keyed_caches(self, ctx):
        """A changed tmdb_base_url/bgm_base_url must not keep serving results
        cached from the old endpoint — reload_settings() must drop the TMDB,
        Mikan, and poster caches plus the LLM parser singleton."""
        ctx.scheduler.running = False
        with (
            patch("module.core.context.settings"),
            patch("module.core.context.reset_shared_client", new=AsyncMock()),
            patch("module.core.context.reset_tmdb_cache") as mock_tmdb,
            patch("module.core.context.reset_mikan_cache") as mock_mikan,
            patch("module.core.context.reset_poster_cache") as mock_poster,
            patch("module.core.context.reset_llm_parser") as mock_llm,
        ):
            await ctx.reload_settings()

        mock_tmdb.assert_called_once()
        mock_mikan.assert_called_once()
        mock_poster.assert_called_once()
        mock_llm.assert_called_once()

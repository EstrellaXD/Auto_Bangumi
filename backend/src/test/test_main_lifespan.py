"""Tests for the application lifespan wiring in main.create_app."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import main
from module.core import AppContext


def _lifespan_ctx(first_run_boot: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.startup = AsyncMock()
    ctx.start_tasks = AsyncMock(return_value=None)
    ctx.stop = AsyncMock()
    ctx.first_run_boot = first_run_boot
    return ctx


class TestCreateApp:
    def test_stores_real_context_on_state(self):
        app = main.create_app()
        assert isinstance(app.state.ctx, AppContext)
        names = [t.name for t in app.state.ctx.scheduler.tasks]
        assert names == ["rss", "rename", "offset_scan", "calendar"]


class TestLifespan:
    def test_startup_runs_and_tasks_scheduled(self):
        """Lifespan awaits startup, schedules start_tasks, stops on shutdown."""
        ctx = _lifespan_ctx(first_run_boot=False)
        with patch("main.AppContext.build", return_value=ctx):
            app = main.create_app()
            with TestClient(app):
                pass
        ctx.startup.assert_awaited_once()
        ctx.start_tasks.assert_called_once()
        ctx.stop.assert_awaited_once()

    def test_first_run_boot_skips_task_start(self):
        """On a first-run boot the background tasks are not auto-started."""
        ctx = _lifespan_ctx(first_run_boot=True)
        with patch("main.AppContext.build", return_value=ctx):
            app = main.create_app()
            with TestClient(app):
                pass
        ctx.startup.assert_awaited_once()
        ctx.start_tasks.assert_not_called()
        ctx.stop.assert_awaited_once()

    def test_startup_failure_aborts_boot(self):
        """A failing startup propagates out of the lifespan (boot aborts)."""
        ctx = _lifespan_ctx(first_run_boot=False)
        ctx.startup = AsyncMock(side_effect=RuntimeError("startup boom"))
        with patch("main.AppContext.build", return_value=ctx):
            app = main.create_app()
            with pytest.raises(RuntimeError, match="startup boom"):
                with TestClient(app):
                    pass

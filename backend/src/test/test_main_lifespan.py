"""Tests for the application lifespan wiring in main.create_app."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
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
    ctx.plugins.start = AsyncMock()
    ctx.plugins.stop = AsyncMock()
    ctx.first_run_boot = first_run_boot
    return ctx


class TestCreateApp:
    def test_import_main_skips_mcp_and_webauthn(self):
        """启动不加载 mcp 与 webauthn 库（其它测试已导入它们，须在子进程里检查）。"""
        src = Path(main.__file__).parent
        code = (
            "import sys, main; print(sorted({'mcp', 'webauthn'} & sys.modules.keys()))"
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            cwd=src.parent,
            env={**os.environ, "PYTHONPATH": str(src)},
            capture_output=True,
            text=True,
        )
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip().splitlines()[-1] == "[]"

    def test_stores_real_context_on_state(self):
        app = main.create_app()
        assert isinstance(app.state.ctx, AppContext)
        names = [t.name for t in app.state.ctx.scheduler.tasks]
        assert names == ["rss", "rename", "offset_scan", "calendar", "update_check"]


class TestLifespan:
    def test_startup_runs_and_tasks_scheduled(self):
        """Lifespan awaits startup, schedules start_tasks, stops on shutdown."""
        ctx = _lifespan_ctx(first_run_boot=False)
        with patch("main.AppContext.build", return_value=ctx):
            app = main.create_app()
            with TestClient(app):
                pass
        ctx.startup.assert_awaited_once()
        ctx.plugins.start.assert_awaited_once()
        ctx.start_tasks.assert_called_once()
        ctx.stop.assert_awaited_once()
        ctx.plugins.stop.assert_awaited_once()

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
        # 迁移失败时插件不应启动（插件 KV 表由迁移创建）
        ctx.plugins.start.assert_not_called()


class TestMcpEndpoint:
    """MCP 走 Streamable HTTP，端点就是 /mcp；会话管理器由应用 lifespan 启动。"""

    HEADERS = {
        "Authorization": "Bearer mcp-token",
        "Accept": "application/json, text/event-stream",
    }

    def test_streamable_http_initialize_and_list_tools(self):
        service = MagicMock()
        service.authenticate_api_token = AsyncMock(return_value=MagicMock())
        with (
            patch("main.AppContext.build", return_value=_lifespan_ctx()),
            patch("module.mcp.security.auth_service", service),
        ):
            app = main.create_app()
            with TestClient(app, follow_redirects=False) as client:
                init = client.post(
                    "/mcp",
                    headers=self.HEADERS,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "0"},
                        },
                    },
                )
                assert init.status_code == 200
                from module.mcp import mcp

                manager = mcp.session_manager
                assert manager._task_group is not None
                session = {"mcp-session-id": init.headers["mcp-session-id"]}
                client.post(
                    "/mcp",
                    headers=self.HEADERS | session,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                )
                listed = client.post(
                    "/mcp",
                    headers=self.HEADERS | session,
                    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                )
                assert listed.status_code == 200
                assert '"list_anime"' in listed.text
                # 旧的 SSE 端点已删除
                assert client.get("/mcp/sse", headers=self.HEADERS).status_code == 404
        # 关停时会话管理器随 lifespan 的任务组停止
        assert manager._task_group is None

    async def test_concurrent_first_requests_build_once(self):
        lazy = main._LazyMcpApp(MagicMock())
        inner = AsyncMock()
        with (
            patch("module.mcp.create_mcp_app", return_value=inner) as build,
            patch("module.mcp.mcp") as server,
        ):
            async with lazy.running():
                await asyncio.gather(
                    *(
                        lazy({"type": "http"}, AsyncMock(), AsyncMock())
                        for _ in range(5)
                    )
                )
        build.assert_called_once()
        server.session_manager.run.assert_called_once()
        assert inner.await_count == 5

    def test_rejected_without_token_or_whitelisted_ip(self):
        with patch("main.AppContext.build", return_value=_lifespan_ctx()):
            app = main.create_app()
            with TestClient(app) as client:
                resp = client.post("/mcp", json={})
        assert resp.status_code == 403

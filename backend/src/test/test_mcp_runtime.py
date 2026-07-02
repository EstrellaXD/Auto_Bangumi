"""Tests for MCP runtime context wiring (module.mcp.runtime)."""

from unittest.mock import MagicMock

from module.mcp import create_mcp_app
from module.mcp.runtime import get_context, set_context
from module.mcp.tools import _get_program_status


class TestRuntimeContext:
    def test_create_mcp_app_stores_context(self):
        sentinel = object()
        try:
            create_mcp_app(sentinel)
            assert get_context() is sentinel
        finally:
            set_context(None)

    def test_get_context_defaults_to_none(self):
        set_context(None)
        assert get_context() is None


class TestProgramStatusReadsContext:
    def test_status_reflects_context(self):
        ctx = MagicMock()
        ctx.is_running = True
        ctx.first_run = False
        set_context(ctx)
        try:
            result = _get_program_status()
        finally:
            set_context(None)
        assert result["running"] is True
        assert result["first_run"] is False

    def test_status_without_context_is_safe(self):
        set_context(None)
        result = _get_program_status()
        assert result["running"] is False
        assert result["first_run"] is True

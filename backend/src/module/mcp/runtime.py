"""Runtime holder for the MCP server's :class:`AppContext`.

The MCP handlers are invoked through the module-level SSE ``Server`` singleton,
outside FastAPI's dependency injection. ``create_mcp_app(ctx)`` stashes the
context here so status tools/resources can read live program state without
importing the old ``module.api.program`` global.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from module.core import AppContext

_context: "Optional[AppContext]" = None


def set_context(ctx: "Optional[AppContext]") -> None:
    global _context
    _context = ctx


def get_context() -> "Optional[AppContext]":
    return _context

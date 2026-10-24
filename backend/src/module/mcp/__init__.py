"""MCP (Model Context Protocol) server for AutoBangumi.

Exposes anime subscriptions, RSS feeds, and download status to MCP clients
(e.g. Claude Desktop) over a local-network-restricted Streamable HTTP endpoint.

Usage::

    from module.mcp import create_mcp_app

    app = create_mcp_app(ctx)  # returns a Starlette ASGI app, route it at /mcp

``mcp`` 与 ``create_mcp_app`` 在首次访问时才导入（mcp 库较重）：main 启动时
只用到 ``module.mcp.security``，不加载 mcp 库。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .server import create_mcp_starlette_app as create_mcp_app
    from .server import mcp


def __getattr__(name: str) -> Any:
    if name not in ("mcp", "create_mcp_app"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    # 导入即注册内置工具与资源
    from . import resources, tools  # noqa: F401
    from .server import create_mcp_starlette_app, mcp

    globals().update(mcp=mcp, create_mcp_app=create_mcp_starlette_app)
    return globals()[name]

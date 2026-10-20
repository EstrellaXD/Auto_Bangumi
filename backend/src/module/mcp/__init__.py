"""MCP (Model Context Protocol) server for AutoBangumi.

Exposes anime subscriptions, RSS feeds, and download status to MCP clients
(e.g. Claude Desktop) over a local-network-restricted Streamable HTTP endpoint.

Usage::

    from module.mcp import create_mcp_app

    app = create_mcp_app(ctx)  # returns a Starlette ASGI app, route it at /mcp
"""

# 导入即注册内置工具与资源
from . import resources, tools  # noqa: F401
from .server import create_mcp_starlette_app as create_mcp_app
from .server import mcp

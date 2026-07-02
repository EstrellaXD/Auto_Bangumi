"""MCP (Model Context Protocol) server for AutoBangumi.

Exposes anime subscriptions, RSS feeds, and download status to MCP clients
(e.g. Claude Desktop) over a local-network-restricted SSE endpoint.

Usage::

    from module.mcp import create_mcp_app

    app = create_mcp_app(ctx)  # returns a Starlette ASGI app, mount at /mcp
"""

from .server import create_mcp_starlette_app as create_mcp_app

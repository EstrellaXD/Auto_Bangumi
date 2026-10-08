"""MCP server assembly for AutoBangumi.

Wires together the MCP ``Server``, SSE transport, tool/resource handlers,
and local-network middleware into a single Starlette ASGI application.

Mount the app returned by ``create_mcp_starlette_app`` at a path prefix
(e.g. ``/mcp``) in the parent FastAPI application to expose the MCP
endpoint at ``/mcp/sse``.
"""

import logging

from mcp import types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from .resources import RESOURCE_TEMPLATES, all_resources, handle_resource
from .runtime import set_context
from .security import McpAccessMiddleware
from .tools import all_tools, handle_tool

logger = logging.getLogger(__name__)

server = Server("autobangumi")
sse = SseServerTransport("/messages/")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return all_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    logger.debug("Tool called: %s", name)
    return await handle_tool(name, arguments)


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    return all_resources()


@server.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return RESOURCE_TEMPLATES


@server.read_resource()
async def read_resource(uri: str) -> str:
    logger.debug("Resource read: %s", uri)
    return await handle_resource(uri)


class _SseEndpoint:
    """``GET /sse`` 的裸 ASGI 端点：建立 SSE 连接并运行 MCP 会话直到客户端断开。

    ``connect_sse`` 自己经 ``send`` 写出整个 HTTP 响应，所以这里不能是返回
    ``Response`` 的普通 endpoint 函数——Starlette 会在 SSE 结束后再发一次
    ``http.response.start``，每次断开都触发 ``AssertionError``。
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async with sse.connect_sse(scope, receive, send) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )


handle_sse = _SseEndpoint()


def create_mcp_starlette_app(ctx=None) -> Starlette:
    """Build and return the MCP Starlette sub-application.

    Routes:
    - ``GET /sse`` - SSE stream for MCP clients
    - ``POST /messages/`` - client-to-server message posting

    ``ctx`` is the application :class:`AppContext`; it is stored so status
    tools/resources can report live program state. ``McpAccessMiddleware`` is
    applied to enforce configurable IP whitelist and bearer token access control.
    """
    set_context(ctx)
    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages", app=sse.handle_post_message),
        ],
    )
    app.add_middleware(McpAccessMiddleware)
    return app

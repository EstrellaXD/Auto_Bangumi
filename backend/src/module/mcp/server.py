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
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from .resources import RESOURCE_TEMPLATES, RESOURCES, handle_resource
from .runtime import set_context
from .security import McpAccessMiddleware
from .tools import TOOLS, handle_tool

logger = logging.getLogger(__name__)

server = Server("autobangumi")
sse = SseServerTransport("/messages/")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    logger.debug("Tool called: %s", name)
    return await handle_tool(name, arguments)


@server.list_resources()
async def list_resources() -> list[types.Resource]:
    return RESOURCES


@server.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return RESOURCE_TEMPLATES


@server.read_resource()
async def read_resource(uri: str) -> str:
    logger.debug("Resource read: %s", uri)
    return await handle_resource(uri)


async def handle_sse(request: Request):
    """Accept an SSE connection, run the MCP session until the client disconnects."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options(),
        )
    return Response()


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

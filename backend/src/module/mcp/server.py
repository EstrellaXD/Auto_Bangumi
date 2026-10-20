"""MCP server assembly for AutoBangumi.

``mcp`` 是 :class:`AutoBangumiMCP`（``MCPServer`` 子类）的单例：内置工具与资源
在 ``tools.py`` / ``resources.py`` 中用 ``@mcp.tool()`` / ``@mcp.resource()``
注册，插件提供的工具与资源在本类的 list / call / read 中追加与分发。

``create_mcp_starlette_app`` 返回 Streamable HTTP 传输的 Starlette 应用，
由 ``main.py`` 以 ``/mcp`` 路由挂载。
"""

import json
import logging
from collections.abc import Iterable
from typing import Any

from mcp import types
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ResourceError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyUrl
from starlette.applications import Starlette

from .plugins import (
    call_plugin_tool,
    list_plugin_resources,
    list_plugin_tools,
    read_plugin_resource,
)
from .runtime import set_context
from .security import McpAccessMiddleware

logger = logging.getLogger(__name__)


def _text(value: Any) -> types.TextContent:
    return types.TextContent(
        type="text", text=json.dumps(value, ensure_ascii=False, default=str)
    )


class AutoBangumiMCP(MCPServer):
    """内置工具与资源走 MCPServer 的注册表，插件的从扩展注册表现取。"""

    async def list_tools(self) -> list[types.Tool]:
        return await super().list_tools() + list_plugin_tools()

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Context | None = None,
    ) -> types.CallToolResult:
        # 结果统一序列化为一段 JSON 文本；内置工具注册时关闭 structured_output，
        # 不声明 outputSchema
        logger.debug("Tool called: %s", name)
        try:
            handled, result = await call_plugin_tool(name, arguments)
            if not handled:
                result = await self._tool_manager.call_tool(
                    name, arguments, context or Context(mcp_server=self)
                )
        except Exception as e:
            logger.exception("Tool %s failed", name)
            # MCPServer 把工具抛出的异常包成 ToolError，原始异常在 __cause__
            error = e.__cause__ or e
            return types.CallToolResult(
                content=[_text({"error": str(error)})], is_error=True
            )
        return types.CallToolResult(content=[_text(result)])

    async def list_resources(self) -> list[types.Resource]:
        return await super().list_resources() + list_plugin_resources()

    async def read_resource(
        self, uri: AnyUrl | str, context: Context | None = None
    ) -> Iterable[ReadResourceContents] | types.InputRequiredResult:
        logger.debug("Resource read: %s", uri)
        try:
            handled, content = await read_plugin_resource(str(uri))
        except Exception as e:
            logger.warning("Plugin resource %s failed: %s", uri, e)
            raise ResourceError(str(e) or type(e).__name__) from e
        if not handled:
            return await super().read_resource(uri, context)
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, default=str)
        return [ReadResourceContents(content=content, mime_type=None)]


mcp = AutoBangumiMCP("autobangumi")


def create_mcp_starlette_app(ctx=None) -> Starlette:
    """Build and return the MCP Starlette sub-application.

    只有一个 Streamable HTTP 端点 ``/mcp``（GET / POST / DELETE）。每次调用都
    新建会话管理器，调用方须在应用 lifespan 中运行 ``mcp.session_manager.run()``。

    ``ctx`` is the application :class:`AppContext`; it is stored so status
    tools/resources can report live program state. ``McpAccessMiddleware`` is
    applied to enforce configurable IP whitelist and bearer token access control.
    """
    set_context(ctx)
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        # 默认 host=127.0.0.1 会开启 DNS rebinding 防护并只放行 localhost 的
        # Host 头，局域网地址与反向代理域名都会被拒（421）。访问控制由
        # McpAccessMiddleware 的 IP 白名单与令牌负责，与原 SSE 端点一致
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    app.add_middleware(McpAccessMiddleware)
    return app

"""插件提供的 MCP 工具与资源（points.MCP_TOOL / points.MCP_RESOURCE）。

每次 list / call 都从扩展注册表现取，插件加载、重载、停用后立即生效。对外
名称加插件 id 前缀以避免与内置及其它插件冲突：

- 工具名 ``<plugin-id>__<id>``：不少 MCP 客户端会把工具名原样交给 LLM API，
  而 Anthropic / OpenAI 的工具名只接受 ``^[a-zA-Z0-9_-]{1,64}$``，所以不用 ``.``。
  插件 id 只含小写字母、数字与连字符，第一个 ``__`` 即为分隔符，不会歧义。
- 资源 URI ``autobangumi://plugins/<plugin-id>/<id>``。

插件处理函数失败或超时会计入该插件的熔断计数。
"""

import asyncio
import logging
import re
from typing import Any

from mcp import types
from pydantic import AnyUrl

from ab_sdk import points
from ab_sdk.mcp import McpResource, McpTool
from module.plugin.host import get_registry
from module.plugin.registry import ProviderEntry

from .runtime import get_context

logger = logging.getLogger(__name__)

TOOL_SEPARATOR = "__"
RESOURCE_PREFIX = "autobangumi://plugins/"
_TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _record(plugin_id: str, reason: str | None) -> None:
    """把调用结果计入插件熔断（MCP 运行时未绑定 AppContext 时跳过）。"""
    ctx = get_context()
    if ctx is None:
        return
    breaker = ctx.plugins.breaker
    if reason is None:
        breaker.record_success(plugin_id)
    else:
        breaker.record_failure(plugin_id, reason)


def _resolve(point: str, expected: type) -> list[tuple[ProviderEntry, Any]]:
    """调用该扩展点的全部插件工厂，跳过失败或类型不符的条目。"""
    resolved = []
    for entry in get_registry().providers(point).values():
        try:
            impl = entry.factory()
            if not isinstance(impl, expected):
                raise TypeError(f"应返回 {expected.__name__}，收到 {type(impl)}")
        except Exception as e:
            reason = f"{point} {entry.id}: {type(e).__name__}: {e}"
            logger.warning("[Plugin:%s] %s", entry.plugin_id, reason)
            _record(entry.plugin_id, reason)
            continue
        resolved.append((entry, impl))
    return resolved


# ------------------------------------------------------------------ tools


def tool_name(plugin_id: str, tool_id: str) -> str:
    return f"{plugin_id}{TOOL_SEPARATOR}{tool_id}"


def _plugin_tools() -> dict[str, tuple[ProviderEntry, McpTool]]:
    tools = {}
    for entry, tool in _resolve(points.MCP_TOOL, McpTool):
        name = tool_name(entry.plugin_id, entry.id)
        if not _TOOL_NAME.match(name):
            logger.warning(
                "[Plugin:%s] MCP 工具名 %r 不合法（仅限字母、数字、_、-，"
                "不超过 64 字符），已跳过",
                entry.plugin_id,
                name,
            )
            continue
        tools[name] = (entry, tool)
    return tools


def list_plugin_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=name, description=tool.description, inputSchema=tool.input_schema
        )
        for name, (_, tool) in sorted(_plugin_tools().items())
    ]


async def call_plugin_tool(name: str, arguments: dict) -> tuple[bool, Any]:
    """调用插件工具；``name`` 不是插件工具时返回 ``(False, None)``。

    插件处理函数的异常会继续抛出（由 ``handle_tool`` 统一转成错误 JSON），
    在此之前计入熔断。
    """
    if TOOL_SEPARATOR not in name:
        return False, None
    found = _plugin_tools().get(name)
    if found is None:
        return False, None
    entry, tool = found
    try:
        result = await asyncio.wait_for(tool.handler(arguments), tool.timeout)
    except Exception as e:
        reason = (
            f"MCP 工具 {entry.id} 超时（{tool.timeout}s）"
            if isinstance(e, TimeoutError)
            else f"MCP 工具 {entry.id}: {type(e).__name__}: {e}"
        )
        _record(entry.plugin_id, reason)
        raise
    _record(entry.plugin_id, None)
    return True, result


# ------------------------------------------------------------------ resources


def resource_uri(plugin_id: str, resource_id: str) -> str:
    return f"{RESOURCE_PREFIX}{plugin_id}/{resource_id}"


def _plugin_resources() -> dict[str, tuple[ProviderEntry, McpResource]]:
    return {
        resource_uri(entry.plugin_id, entry.id): (entry, resource)
        for entry, resource in _resolve(points.MCP_RESOURCE, McpResource)
    }


def list_plugin_resources() -> list[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl(uri),
            name=resource.name,
            description=resource.description or None,
            mimeType=resource.mime_type,
        )
        for uri, (_, resource) in sorted(_plugin_resources().items())
    ]


async def read_plugin_resource(uri: str) -> tuple[bool, Any]:
    """读取插件资源；``uri`` 不是插件资源时返回 ``(False, None)``。"""
    if not uri.startswith(RESOURCE_PREFIX):
        return False, None
    found = _plugin_resources().get(uri)
    if found is None:
        return False, None
    entry, resource = found
    try:
        result = await resource.handler()
    except Exception as e:
        _record(entry.plugin_id, f"MCP 资源 {entry.id}: {type(e).__name__}: {e}")
        raise
    _record(entry.plugin_id, None)
    return True, result

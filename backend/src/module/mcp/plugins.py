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
from collections.abc import Callable
from typing import Any

from mcp import types
from pydantic import AnyUrl

from ab_sdk import points
from ab_sdk.mcp import DEFAULT_TOOL_TIMEOUT, McpResource, McpTool
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


def _resolve(
    point: str, expected: type, spec: Callable[[ProviderEntry, Any], Any]
) -> list[tuple[ProviderEntry, Any, Any]]:
    """调用该扩展点的全部插件工厂并用 ``spec`` 生成对外的 MCP 描述，
    跳过失败、类型不符或字段不合法（MCP 模型校验失败）的条目。"""
    resolved = []
    for entry in get_registry().providers(point).values():
        try:
            impl = entry.factory()
            if not isinstance(impl, expected):
                raise TypeError(f"应返回 {expected.__name__}，收到 {type(impl)}")
            described = spec(entry, impl)
        except Exception as e:
            reason = f"{point} {entry.id}: {type(e).__name__}: {e}"
            logger.warning("[Plugin:%s] %s", entry.plugin_id, reason)
            _record(entry.plugin_id, reason)
            continue
        resolved.append((entry, impl, described))
    return resolved


# ------------------------------------------------------------------ tools


def tool_name(plugin_id: str, tool_id: str) -> str:
    return f"{plugin_id}{TOOL_SEPARATOR}{tool_id}"


def _tool_spec(entry: ProviderEntry, tool: McpTool) -> types.Tool:
    return types.Tool(
        name=tool_name(entry.plugin_id, entry.id),
        description=tool.description,
        inputSchema=tool.input_schema,
    )


def _plugin_tools() -> dict[str, tuple[ProviderEntry, McpTool, types.Tool]]:
    tools = {}
    for entry, tool, spec in _resolve(points.MCP_TOOL, McpTool, _tool_spec):
        name = spec.name
        if not _TOOL_NAME.match(name):
            logger.warning(
                "[Plugin:%s] MCP 工具名 %r 不合法（仅限字母、数字、_、-，"
                "不超过 64 字符），已跳过",
                entry.plugin_id,
                name,
            )
            continue
        tools[name] = (entry, tool, spec)
    return tools


def list_plugin_tools() -> list[types.Tool]:
    return [spec for _, (_, _, spec) in sorted(_plugin_tools().items())]


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
    entry, tool, _ = found
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


def _resource_spec(entry: ProviderEntry, resource: McpResource) -> types.Resource:
    return types.Resource(
        uri=AnyUrl(resource_uri(entry.plugin_id, entry.id)),
        name=resource.name,
        description=resource.description or None,
        mimeType=resource.mime_type,
    )


def _plugin_resources() -> dict[str, tuple[ProviderEntry, McpResource, types.Resource]]:
    # 以 AnyUrl 规范化后的 URI 为键：含空格或非 ASCII 字符的 id 会被百分号编码，
    # 客户端读取时传回的正是列表里的编码形式
    return {
        str(spec.uri): (entry, resource, spec)
        for entry, resource, spec in _resolve(
            points.MCP_RESOURCE, McpResource, _resource_spec
        )
    }


def list_plugin_resources() -> list[types.Resource]:
    return [spec for _, (_, _, spec) in sorted(_plugin_resources().items())]


async def read_plugin_resource(uri: str) -> tuple[bool, Any]:
    """读取插件资源；``uri`` 不是插件资源时返回 ``(False, None)``。"""
    if not uri.startswith(RESOURCE_PREFIX):
        return False, None
    found = _plugin_resources().get(uri)
    if found is None:
        return False, None
    entry, resource, _ = found
    # McpResource 没有超时字段，沿用工具的默认超时
    try:
        result = await asyncio.wait_for(resource.handler(), DEFAULT_TOOL_TIMEOUT)
    except Exception as e:
        reason = (
            f"MCP 资源 {entry.id} 超时（{DEFAULT_TOOL_TIMEOUT}s）"
            if isinstance(e, TimeoutError)
            else f"MCP 资源 {entry.id}: {type(e).__name__}: {e}"
        )
        _record(entry.plugin_id, reason)
        raise
    _record(entry.plugin_id, None)
    return True, result

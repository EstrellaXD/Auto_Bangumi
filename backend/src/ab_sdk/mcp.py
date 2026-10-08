"""MCP 工具与资源契约。

插件用 ``@provider(points.MCP_TOOL, id="search")`` 返回 :class:`McpTool`，
用 ``@provider(points.MCP_RESOURCE, id="stats")`` 返回 :class:`McpResource`。
``id`` 只需在插件内唯一，宿主对外暴露时加上插件 id 前缀以避免冲突：

- 工具名：``<plugin-id>__<id>``（双下划线。不用 ``.``，因为不少 MCP 客户端
  所接的 LLM API 只接受 ``^[a-zA-Z0-9_-]{1,64}$`` 的工具名）
- 资源 URI：``autobangumi://plugins/<plugin-id>/<id>``

MCP 端点（``/mcp``）沿用宿主的访问控制（IP 白名单 / ``scope=mcp`` 令牌），
插件无需自行鉴权。
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

DEFAULT_TOOL_TIMEOUT = 60.0


@dataclass(frozen=True)
class McpTool:
    """一个 MCP 工具。

    ``handler`` 接收客户端传入的参数字典（已按 ``input_schema`` 校验），返回
    可 JSON 序列化的结果；宿主把结果序列化后作为文本内容返回给客户端。抛出的
    异常会以 ``{"error": "..."}`` 返回，并计入插件熔断。
    """

    description: str
    handler: Callable[[dict[str, Any]], Awaitable[Any]]
    # JSON Schema；默认不接受参数
    input_schema: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    # 执行超时（秒）
    timeout: float = DEFAULT_TOOL_TIMEOUT


@dataclass(frozen=True)
class McpResource:
    """一个只读的 MCP 资源。

    ``handler`` 不接受参数，返回字符串（原样返回）或可 JSON 序列化的对象
    （宿主序列化为 JSON）。
    """

    name: str
    handler: Callable[[], Awaitable[Any]]
    description: str = ""
    mime_type: str = "application/json"

"""宿主声明的扩展点名称。插件用这些常量而不是手写字符串。

Provider 扩展点（``@provider``）：

- ``DOWNLOADER``：返回 :data:`ab_sdk.downloader.DownloaderFactory`，id 即
  ``downloader.type`` 的取值
- ``NOTIFIER``：返回 :data:`ab_sdk.notify.NotifierFactory`，id 即通知渠道的
  ``type``
- ``LLM_PROVIDER``：返回 :class:`ab_sdk.llm.LLMProviderAdapter` 子类
- ``SEARCH_SITE``：返回 :class:`ab_sdk.search.SearchSite`，id 即站点名
- ``SCHEDULED_TASK``：返回 :class:`ab_sdk.tasks.ScheduledTask`
"""

DOWNLOADER = "downloader"
NOTIFIER = "notifier"
LLM_PROVIDER = "llm_provider"
SEARCH_SITE = "search_site"
SCHEDULED_TASK = "scheduled_task"

# --- P5：外部接口与通知模板 ---
#
# Provider 扩展点（id 只需在插件内唯一，宿主对外暴露时加插件 id 前缀）：
#
# - ``API_ROUTER``：返回 ``fastapi.APIRouter``，挂载于
#   ``/api/v1/plugins/<plugin-id>/``，强制登录鉴权
# - ``MCP_TOOL``：返回 :class:`ab_sdk.mcp.McpTool`，MCP 工具名为
#   ``<plugin-id>__<id>``
# - ``MCP_RESOURCE``：返回 :class:`ab_sdk.mcp.McpResource`，URI 为
#   ``autobangumi://plugins/<plugin-id>/<id>``
#
# Transform 钩子（``@hook``）：
#
# - ``MESSAGE_TEMPLATE``：签名 ``(message: RenderedMessage, event: SystemEvent,
#   channel: str) -> RenderedMessage | None``，在系统事件推送到外部通知渠道前
#   改写标题与正文；``channel`` 为渠道类型（如 ``telegram``）

API_ROUTER = "api_router"
MCP_TOOL = "mcp_tool"
MCP_RESOURCE = "mcp_resource"
MESSAGE_TEMPLATE = "message_template"

"""宿主声明的扩展点名称。插件用这些常量而不是手写字符串。

Provider 扩展点（``@provider``）：

- ``DOWNLOADER``：返回 :data:`ab_sdk.downloader.DownloaderFactory`，id 即
  下载器实例的 ``provider``（``plugins.instances[].provider``）
- ``NOTIFIER``：返回 :data:`ab_sdk.notify.NotifierFactory`，id 即通知渠道的
  ``type``
- ``LLM_PROVIDER``：返回 :class:`ab_sdk.llm.LLMProviderAdapter` 子类
- ``SEARCH_SITE``：返回 :class:`ab_sdk.search.SearchSite`，id 即站点名
- ``SCHEDULED_TASK``：返回 :class:`ab_sdk.tasks.ScheduledTask`
- ``METADATA_PROVIDER``：返回 :class:`ab_sdk.ingest.MetadataProvider`，id 即
  RSS 订阅的「解析器」（``RSSItem.parser``）取值

钩子扩展点（``@hook``，契约见 :mod:`ab_sdk.ingest`）：

- ``TORRENT_FILTER``（filter）：决定已匹配规则的种子是否下载
- ``TITLE_PARSED``（transform）：修正标题解析结果
- ``TORRENT_ADDING``（transform）：修改发给下载器的添加请求
- ``HTTP_REQUEST``（transform）：修改宿主 GET 请求的请求头
"""

DOWNLOADER = "downloader"
NOTIFIER = "notifier"
LLM_PROVIDER = "llm_provider"
SEARCH_SITE = "search_site"
SCHEDULED_TASK = "scheduled_task"

# --- ingest ---
METADATA_PROVIDER = "metadata_provider"
TORRENT_FILTER = "torrent.filter"
TITLE_PARSED = "title.parsed"
TORRENT_ADDING = "torrent.adding"
HTTP_REQUEST = "http.request"

# --- 外部接口与通知模板 ---
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

# --- organize（契约见 :mod:`ab_sdk.rename`） ---
#
# Provider 扩展点：
#
# - ``RENAME_STRATEGY``：返回 :class:`ab_sdk.rename.RenameStrategy`，id 即
#   ``plugins.slots.rename_strategy`` 的取值。宿主自带 ``none``（不改名），
#   内置插件 ``rename`` 提供 ``pn``、``advance``、``template``
# - ``MEDIA_FILES``：返回 :class:`ab_sdk.rename.MediaFiles`
# - ``CONFLICT_POLICY``：返回 :class:`ab_sdk.rename.ConflictPolicy`
#
# 事件（``@subscribe``）：``file.renamed``（:class:`ab_sdk.events.FileRenamed`）、
# ``torrent.organized``（:class:`ab_sdk.events.TorrentOrganized`）

RENAME_STRATEGY = "rename_strategy"
MEDIA_FILES = "media_files"
CONFLICT_POLICY = "conflict_policy"

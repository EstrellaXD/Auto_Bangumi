"""宿主声明的扩展点名称。插件用这些常量而不是手写字符串。

Provider 扩展点（``@provider``）：

- ``DOWNLOADER``：返回 :data:`ab_sdk.downloader.DownloaderFactory`，id 即
  ``downloader.type`` 的取值
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

# --- P3 ingest ---
METADATA_PROVIDER = "metadata_provider"
TORRENT_FILTER = "torrent.filter"
TITLE_PARSED = "title.parsed"
TORRENT_ADDING = "torrent.adding"
HTTP_REQUEST = "http.request"

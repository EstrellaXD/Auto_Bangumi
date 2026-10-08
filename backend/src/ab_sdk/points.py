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

"""非「新集数」通知的类型化事件负载。

刻意与 ``Notification``（module/models/bangumi.py，仅描述「新集数下载完成」）
分开：RSS 订阅失败、下载添加失败、偏移量待确认等事件携带的字段与集数通知完全
无关，硬塞进 ``Notification`` 只会制造出没有意义的 season/episode 占位值。

4.0 起事件类定义在 ``ab_sdk.events``（插件订阅时需要 import 它们），这里只做
再导出，宿主代码的 import 路径保持不变。每个事件同时服务三个消费方：

- 外部推送（Telegram/Bark 等）：``describe() -> (标题, 正文)`` 渲染中文文案，
  插件可通过 ``message_template`` 钩子改写；
- 站内通知中心：``kind``/``severity``/``once``/``dedup_key()``/``payload()``
  提供结构化字段，前端按 kind + payload 做多语言渲染（``i18n()`` 给出 key），
  describe() 文案作为未知 kind 的兜底展示。``once=True`` 表示同 dedup_key
  终生只入库一次（如"新版本可用"，已读后同一版本不再提醒）；
- 事件总线：``NotificationManager.send_event`` 把事件发布到插件事件总线。

``SystemEvent`` 从封闭的 Union 改为基类：插件定义的可通知事件同样可以送进
``send_event``。
"""

from ab_sdk.events import (
    DownloaderUnavailableEvent,
    DownloadFailureEvent,
    LLMAuthFailureEvent,
    LLMPluginInstallFailedEvent,
    OffsetReviewEvent,
    RenameConflictEvent,
    RssFailureEvent,
    SystemEvent,
    UpdateAppliedEvent,
    UpdateAvailableEvent,
)

__all__ = [
    "DownloadFailureEvent",
    "DownloaderUnavailableEvent",
    "LLMAuthFailureEvent",
    "LLMPluginInstallFailedEvent",
    "OffsetReviewEvent",
    "RenameConflictEvent",
    "RssFailureEvent",
    "SystemEvent",
    "UpdateAppliedEvent",
    "UpdateAvailableEvent",
]

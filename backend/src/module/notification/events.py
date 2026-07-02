"""非「新集数」通知的类型化事件负载。

刻意与 ``Notification``（module/models/bangumi.py，仅描述「新集数下载完成」）
分开：RSS 订阅失败、下载添加失败、偏移量待确认三类事件携带的字段与集数通知完全
无关，硬塞进 ``Notification`` 只会制造出没有意义的 season/episode 占位值。
"""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RssFailureEvent:
    """RSS 订阅连接状态从正常变为异常（仅状态翻转时触发一次，而非每个 tick）。"""

    rss_name: str
    rss_url: str
    error: str

    def describe(self) -> tuple[str, str]:
        """返回该事件的默认 (标题, 正文)。"""
        return (
            "RSS 订阅连接异常",
            f"订阅：{self.rss_name}\n地址：{self.rss_url}\n错误：{self.error}",
        )


@dataclass(slots=True, frozen=True)
class DownloadFailureEvent:
    """匹配到的种子在（内置 HTTP 重试后）仍添加下载器失败。"""

    official_title: str
    torrent_name: str

    def describe(self) -> tuple[str, str]:
        return (
            "种子添加失败",
            f"番剧：{self.official_title}\n种子：{self.torrent_name}\n"
            "重试后仍添加失败，请检查下载器连接。",
        )


@dataclass(slots=True, frozen=True)
class OffsetReviewEvent:
    """番剧被标记为需要人工确认季度/集数偏移。"""

    official_title: str
    reason: str

    def describe(self) -> tuple[str, str]:
        return (
            "集数偏移待确认",
            f"番剧：{self.official_title}\n原因：{self.reason}\n请前往设置页确认偏移量。",
        )


# 除「新集数」以外的通知事件的联合类型。
SystemEvent = RssFailureEvent | DownloadFailureEvent | OffsetReviewEvent

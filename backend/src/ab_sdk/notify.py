"""通知渠道契约。

插件用 ``@provider(points.NOTIFIER, id="mychannel")`` 返回一个
:data:`NotifierFactory`。用户在通知设置里添加 ``type`` 为该 id 的渠道后，
宿主会用该渠道条目构造 :class:`Notifier`。渠道的凭据等配置建议放在插件自己的
``config_model`` 里（通过 ``self.config`` 读取）；渠道条目只携带模板和
条目上的额外字段。
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class NotifierSettings:
    """通知设置中的一条渠道配置。"""

    # 单集通知模板（{{title}}/{{season}}/{{episode}}/{{poster_url}}），可为空
    template: str | None = None
    # 渠道条目上除通用字段以外的其它字段
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NotificationMessage:
    kind: Literal["episode", "event"]
    title: str
    body: str
    # 以下仅 kind == "episode" 时有值
    official_title: str | None = None
    season: int | None = None
    episode: int | float | None = None
    # 配置了 notification.base_url 时为可公开访问的海报地址
    poster_url: str | None = None


class Notifier(Protocol):
    async def send(self, message: NotificationMessage) -> bool:
        """投递一条消息，成功返回 True。"""
        ...

    async def test(self) -> tuple[bool, str]:
        """发送测试消息，返回 (是否成功, 说明)。"""
        ...


NotifierFactory = Callable[[NotifierSettings], Notifier]


@dataclass(frozen=True)
class RenderedMessage:
    """``message_template`` 钩子处理的消息：系统事件推送前的标题与正文。

    初始值来自事件的 ``describe()``；钩子返回新的 RenderedMessage 即可改写，
    返回 None 表示不修改。多个钩子按优先级依次处理，后一个拿到前一个的结果。
    """

    title: str
    body: str

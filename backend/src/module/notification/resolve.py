"""按渠道 ``type`` 从扩展注册表构造通知渠道（内置与插件统一入口）。"""

from typing import TYPE_CHECKING

from ab_sdk import points
from ab_sdk.notify import NotificationMessage, Notifier, NotifierSettings
from module.models.bangumi import Notification
from module.plugin.host import CORE, get_registry

from .base import NotificationProvider

if TYPE_CHECKING:
    from module.models.config import NotificationProvider as ProviderConfig


class PluginNotifier(NotificationProvider):
    """把插件的 :class:`ab_sdk.notify.Notifier` 适配为宿主的渠道接口。

    模板渲染与海报地址仍由宿主负责，插件拿到的是渲染好的消息。
    """

    def __init__(self, config: "ProviderConfig", notifier: Notifier) -> None:
        super().__init__(config)
        self._notifier = notifier

    async def send(self, notification: Notification) -> bool:
        return await self._notifier.send(
            NotificationMessage(
                kind="episode",
                title=notification.official_title,
                body=self._format_message(notification),
                official_title=notification.official_title,
                season=notification.season,
                episode=notification.episode,
                poster_url=self._poster_url(notification),
            )
        )

    async def _deliver_text(self, title: str, body: str) -> bool:
        return await self._notifier.send(
            NotificationMessage(kind="event", title=title, body=body)
        )

    async def test(self) -> tuple[bool, str]:
        return await self._notifier.test()


def build_provider(config: "ProviderConfig") -> NotificationProvider | None:
    """构造渠道实例；``type`` 未登记时返回 None。"""
    # 先按原样匹配（插件 id 可含大写），再按小写兼容内置渠道的旧配置
    entries = get_registry().providers(points.NOTIFIER)
    entry = entries.get(config.type) or entries.get(config.type.lower())
    if entry is None:
        return None
    impl = entry.factory()
    if entry.plugin_id == CORE:
        # 内置渠道：impl 是 NotificationProvider 子类，直接接收整条配置
        return impl(config)
    # extra = 未知字段 + 已填写的已声明字段（group、icon 等同时是 Bark 的字段，
    # 声明后不在 model_extra 里）；type/enabled/template 由宿主处理，不放进去。
    # 已声明字段按别名取同名属性（token、url 等），与内置渠道一样展开 $VAR
    unknown = config.model_extra or {}
    declared = config.model_dump(
        by_alias=True,
        exclude_none=True,
        exclude={"type", "enabled", "template", *unknown},
    )
    expanded = {k: getattr(config, k) for k in declared}
    extra = {k: v for k, v in expanded.items() if v != ""} | unknown
    settings = NotifierSettings(template=config.template, extra=extra)
    return PluginNotifier(config, impl(settings))

"""系统事件推送文案：默认 ``describe()``，经 ``message_template`` 钩子改写。"""

import logging

from ab_sdk import points
from ab_sdk.notify import RenderedMessage
from module.notification.events import SystemEvent
from module.plugin.host import get_runner

logger = logging.getLogger(__name__)


async def render_event(event: SystemEvent, channel: str) -> tuple[str, str]:
    """返回推送到 ``channel`` 渠道的 (标题, 正文)。

    没有插件挂 ``message_template`` 钩子时与 ``event.describe()`` 完全一致；
    钩子失败、超时或返回值不是 ``RenderedMessage`` 时沿用上一步的结果（并计入
    该插件的熔断）。
    """
    title, body = event.describe()
    runner = get_runner()
    if runner is None:
        return title, body
    try:
        message = await runner.transform(
            points.MESSAGE_TEMPLATE,
            RenderedMessage(title, body),
            event,
            channel,
            expect=RenderedMessage,
        )
    except Exception:
        # 单个钩子的失败已在 runner 内隔离；这里兜底的是运行时本身的异常
        # （如扩展点未声明），任何情况下都不能让通知因模板而发不出去
        logger.warning("[Notification] 渲染通知模板失败，使用默认文案", exc_info=True)
        return title, body
    return message.title, message.body

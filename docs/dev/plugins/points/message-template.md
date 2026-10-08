# 通知文案模板（message_template）

transform 钩子。系统事件推送到外部渠道前，依次经过它。钩子拿到默认文案、事件和渠道类型，返回新的 `RenderedMessage` 即可改写，返回 `None` 表示不修改。

```python
from ab_sdk import Plugin, hook, points
from ab_sdk.notify import RenderedMessage


class Alerts(Plugin):
    @hook(points.MESSAGE_TEMPLATE)
    def template(self, message: RenderedMessage, event, channel: str):
        if event.kind != "rss_failure":
            return None
        if channel == "telegram":
            return RenderedMessage(
                f"[告警] {message.title}", f"<b>{event.rss_name}</b>\n{event.error}"
            )
        return None
```

- 只影响外部推送。通知中心里的文案由前端按 `i18n()` 渲染，不受影响。
- 钩子对每个启用的渠道各调用一次；`channel` 是渠道类型，如 `telegram`。
- 钩子出错或超时时沿用上一步的文案，并计入熔断；返回值类型不对时整条消息回退到默认文案。
- 「新集数」通知暂不经过该钩子，仍使用通知渠道里配置的单集模板。

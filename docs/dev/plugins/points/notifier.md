# 通知渠道（notifier）

增加一个通知渠道。`@provider(points.NOTIFIER, id=...)` 返回 `NotifierFactory`：接收渠道条目 `NotifierSettings`，返回 `Notifier`。用户在 设置 → 通知 → 添加渠道 时，类型下拉框会多出该 `id`。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Channel:
    def __init__(self, settings: NotifierSettings) -> None:
        self.settings = settings

    async def send(self, message: NotificationMessage) -> bool:
        ...  # 投递成功返回 True

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(NotificationMessage(kind="event", title="AB", body="测试"))
        return ok, "ok" if ok else "发送失败"


class MyPlugin(Plugin):
    @provider(points.NOTIFIER, id="my-push")
    def channel(self) -> NotifierFactory:
        return Channel
```

## 契约

- `send(message)` 返回 `bool`。后端拒绝消息时返回 `False`，不要抛异常。
- `test()` 返回 `(是否成功, 说明)`。
- `NotificationMessage.kind` 为 `episode`（新集数；带 `official_title`、`season`、`episode`、`poster_url`）或 `event`（系统事件）。
- 凭据放在插件自己的 `config_model` 里，通过 `self.config` 读取。渠道条目 `NotifierSettings` 只带通用模板 `template` 和其余字段 `extra`。
- 要改写推送文案，用 [通知文案模板](/dev/plugins/points/message-template) 钩子。

## 测试

```python
from ab_sdk.testing import NotifierContract

class TestChannel(NotifierContract):
    def create(self):
        ...                    # 后端接受消息的渠道

    def create_failing(self):
        ...                    # 可选：后端拒绝消息的渠道
```

示例：`examples/plugins/ntfy-notifier`。

# Notifier (notifier)

Adds a notification channel. `@provider(points.NOTIFIER, id=...)` returns a `NotifierFactory`. The factory receives the channel entry `NotifierSettings` and returns a `Notifier`. When the user adds a channel in Settings → Notification, the type list shows this `id`.

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Channel:
    def __init__(self, settings: NotifierSettings) -> None:
        self.settings = settings

    async def send(self, message: NotificationMessage) -> bool:
        ...  # return True when the message is delivered

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(NotificationMessage(kind="event", title="AB", body="test"))
        return ok, "ok" if ok else "send failed"


class MyPlugin(Plugin):
    @provider(points.NOTIFIER, id="my-push")
    def channel(self) -> NotifierFactory:
        return Channel
```

## Contract

- `send(message)` returns a `bool`. When the backend refuses the message, return `False`. Do not raise an exception.
- `test()` returns `(success, message)`.
- `NotificationMessage.kind` is `episode` (a new episode; it has `official_title`, `season`, `episode`, `poster_url`) or `event` (a system event).
- Put the credentials in the `config_model` of the plugin and read them through `self.config`. The channel entry `NotifierSettings` has only the common template `template` and the other fields in `extra`.
- To rewrite the push text, use the [message template](/en/dev/plugins/points/message-template) hook.

## Tests

```python
from ab_sdk.testing import NotifierContract

class TestChannel(NotifierContract):
    def create(self):
        ...                    # a channel whose backend accepts messages

    def create_failing(self):
        ...                    # optional: a channel whose backend refuses messages
```

Example: `examples/plugins/ntfy-notifier`.

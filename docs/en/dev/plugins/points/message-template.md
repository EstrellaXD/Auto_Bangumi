# Message Template (message_template)

A transform hook. Before AB pushes a system event to an external channel, the event passes through these hooks in order. A hook receives the default text, the event and the channel type. Return a new `RenderedMessage` to rewrite the text. `None` means no change.

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
                f"[ALERT] {message.title}", f"<b>{event.rss_name}</b>\n{event.error}"
            )
        return None
```

- The hook affects only the external push. The frontend renders the text in the notification center from `i18n()`, so it does not change.
- AB calls the hook one time for each enabled channel. `channel` is the channel type, for example `telegram`.
- If a hook fails, times out or returns a value that is not a `RenderedMessage`, AB keeps the text of the previous step. The failure counts toward the breaker. The next hooks run as usual.
- "New episode" notifications do not pass through this hook yet. They still use the single-episode template of the notification channel.

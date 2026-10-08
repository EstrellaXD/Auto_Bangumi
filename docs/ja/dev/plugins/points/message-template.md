# 通知メッセージテンプレート (message_template)

transform フックです。システムイベントを外部チャンネルへプッシュする前に、イベントはこのフックを順に通ります。フックは既定の文面、イベント、チャンネルの種類を受け取ります。新しい `RenderedMessage` を返すと文面を書き換えられます。`None` は変更なしです。

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
                f"[警告] {message.title}", f"<b>{event.rss_name}</b>\n{event.error}"
            )
        return None
```

- フックが影響するのは外部へのプッシュだけです。通知センターの文面は、フロントエンドが `i18n()` から描画するので変わりません。
- フックは、有効な各チャンネルに対して 1 回ずつ呼ばれます。`channel` はチャンネルの種類で、例えば `telegram` です。
- フックが失敗した、タイムアウトした、または `RenderedMessage` 以外を返した場合は、前の段階の文面を使い、失敗はブレーカーに数えられます。後続のフックは通常どおり実行されます。
- 「新しい話」の通知は、まだこのフックを通りません。通知チャンネルに設定した 1 話用のテンプレートを使います。

# 通知チャンネル (notifier)

通知チャンネルを追加します。`@provider(points.NOTIFIER, id=...)` は `NotifierFactory` を返します。ファクトリはチャンネルのエントリ `NotifierSettings` を受け取り、`Notifier` を返します。ユーザーが設定 → 通知でチャンネルを追加するとき、種類の一覧にこの `id` が表示されます。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Channel:
    def __init__(self, settings: NotifierSettings) -> None:
        self.settings = settings

    async def send(self, message: NotificationMessage) -> bool:
        ...  # 配信に成功したら True を返す

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(NotificationMessage(kind="event", title="AB", body="test"))
        return ok, "ok" if ok else "送信に失敗しました"


class MyPlugin(Plugin):
    @provider(points.NOTIFIER, id="my-push")
    def channel(self) -> NotifierFactory:
        return Channel
```

## コントラクト

- `send(message)` は `bool` を返します。バックエンドがメッセージを拒否したときは `False` を返してください。例外を送出しないでください。
- `test()` は `(成功したか, 説明)` を返します。
- `NotificationMessage.kind` は `episode`（新しい話。`official_title`、`season`、`episode`、`poster_url` を持つ）または `event`（システムイベント）です。
- 認証情報はプラグイン自身の `config_model` に置き、`self.config` で読みます。チャンネルのエントリ `NotifierSettings` が持つのは、共通のテンプレート `template` と、その他のフィールド `extra` だけです。
- プッシュの文面を書き換えるには、[通知メッセージテンプレート](/ja/dev/plugins/points/message-template) フックを使います。

## テスト

```python
from ab_sdk.testing import NotifierContract

class TestChannel(NotifierContract):
    def create(self):
        ...                    # バックエンドがメッセージを受け付けるチャンネル

    def create_failing(self):
        ...                    # 任意：バックエンドがメッセージを拒否するチャンネル
```

例：`examples/plugins/ntfy-notifier`。

# LLM プロバイダー (llm_provider)

LLM 解析プロバイダーを追加します。`@provider(points.LLM_PROVIDER, id=...)` は `ab_sdk.llm.LLMProviderAdapter` のサブクラスを返します。**`id` は `info.id` と同じにする必要があります。** ユーザーは設定 → LLM → プロバイダーで選びます。組み込みプロバイダーの id は上書きできません。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.llm import AdapterContext, LLMProviderAdapter, ProviderInfo


class MyAdapter(LLMProviderAdapter):
    info = ProviderInfo(
        id="my-llm",
        display_name="My LLM",
        auth_kind="api_key",
        needs_base_url=True,
        default_model="my-model",
    )
    ...  # parse / list_models などの抽象メソッドを実装


class MyPlugin(Plugin):
    @provider(points.LLM_PROVIDER, id="my-llm")
    def adapter(self):
        return MyAdapter
```

## 要点

- `ProviderInfo` がフロントエンドのフォームとプロバイダー一覧を決めます。`auth_kind` は `api_key`、`oauth`、`device_code` のいずれかです。
- アダプターは `AdapterContext` から、モデル名、キー、`base_url`、タイムアウト、プロキシ対応の httpx クライアントのファクトリを受け取ります。グローバル設定は読みません。
- サブスクリプション型のプロバイダー（`oauth` / `device_code`）は、認証フローのフック（`AuthChallenge`、`TokenSet`）を実装します。認証情報が無効になり、更新にも失敗したときは `AuthExpiredError` を送出します。AB はこのプロバイダーのブレーカーを作動させ、`llm_auth_failure` イベントを送ります。
- `plugin.json` 形式の既存の LLM プラグイン（`llm-plugins` として公開）は引き続き使えます。新しいプラグインは `plugin.toml` とこの拡張ポイントを使います。

# バージョン競合ポリシー (conflict_policy)

新しいトレントの正規のファイル名を、別のトレントが既に使っている場合に、古いものを残すか置き換えるかを決めます。典型的な場面は、同じ話の v2 リリースです。`@provider(points.CONFLICT_POLICY, id=...)` は `ConflictPolicy` を返します。

```python
from ab_sdk.rename import ConflictDecision, ConflictRequest

class ReplaceUpgradesOnly:
    def decide(self, request: ConflictRequest) -> ConflictDecision:
        if request.strict_upgrade:
            return ConflictDecision("replace")
        return ConflictDecision("hold", "同じリリースの上位バージョンではありません")
```

- `ConflictRequest`：`target_path`、`incoming`（新しいトレント）、`owners`（その名前を使っているトレント）、`strict_upgrade`（唯一の使用者が新しいトレントと同じリリースで、新しいトレントのバージョン番号が上位）。
- `hold` は古いファイルを残し、新しいトレントは待機します。`reason` はユーザーに表示されます。`replace` は**古いタスクとそのファイルを削除します**。
- ホストが `replace` を実行するのは、「使用者が 1 つだけ、両方が単一ファイルのトレント、両方の解析結果が完全」の場合だけです。それ以外はすべて `hold` として扱います。
- ホストは `hold` と `replace` を持っています。これが設定「バージョン競合ポリシー」の 2 つの選択肢です。`plugins.slots.conflict_policy` でポリシーを選びます（既定は `hold`）。選ばれた id が登録されていない場合は `hold` に戻ります。

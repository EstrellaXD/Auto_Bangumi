# 設定フォーム

プラグインは `config_model`（pydantic モデル）を宣言します。WebUI は設定 → プラグインで、これからフォームを自動生成します。プラグイン作者がフロントエンドを書く必要はありません。

```python
from pydantic import BaseModel, Field
from ab_sdk import Plugin, secret_field

class Options(BaseModel):
    endpoint: str = Field("https://push.example.com", title="送信先")
    key: str = secret_field(description="プッシュキー")
    retries: int = Field(3, ge=0, le=10, title="リトライ回数")

class MyPlugin(Plugin[Options]):
    config_model = Options
```

## フィールドの型

| Python の型 | フォームの部品 |
| --- | --- |
| `str` | テキストボックス |
| `secret_field()` で宣言した `str` | パスワードボックス |
| `int` / `float` | 数値ボックス（`int` は入力後に整数へ丸めます） |
| `bool` | スイッチ |
| `Literal[...]` / `Enum` | ドロップダウン |
| `list[str]` | タグ入力 |
| `list[<BaseModel>]` | オブジェクトの配列：1 行ごとにサブフィールドの組。行の追加と削除ができます |
| その他（`dict`、入れ子のオブジェクト） | 「未対応のフィールド」と表示されます。`config.json` を直接編集してください |

`Field(title=..., description=...)` はラベルと説明文になります。`Optional[T]` は `T` として描画されます。保存されていないフィールドには既定値が入ります。

## 検証

- 保存時に AB がモデルで検証します。不正な値には HTTP 422 を返し、設定には書き込みません。
- 詳しい検証は `field_validator` で行います。たとえば、組み込みの `rename` は保存時にテンプレートを一度描画します。間違ったテンプレートはその場で拒否されます。
- 既定値のない必須フィールドは、初回の有効化時に未設定です。このときプラグインはエラー状態になります。ユーザーが入力して保存すると、プラグインは自動で復旧します。
- 無効なプラグインでもフォームは表示されます。AB は信頼済みのプラグインのコードを import し、`config_model` だけを読みます。`setup` は呼びません。まだ許可されていないローカルプラグイン（未署名で「未署名プラグインを許可」がオフ）はコードを実行しないため、フォームもありません。

## 秘密フィールド

`secret_field()` はパスワード、トークン、Cookie などを宣言します。

- WebUI はパスワードボックスで表示します。
- 設定を読み取る API はマスクだけを返します。ブラウザが元の値を受け取ることはありません。
- 保存時にマスクを受け取ると、AB は元の値を保持します。マスク処理は入れ子の構造にも働き、オブジェクト配列の行の中の秘密フィールドも対象です。行数が変わって元の行と対応付けられない場合、その秘密フィールドは空になり、ユーザーが再入力します。

設定は `config.json` の `plugins.options.<プラグイン id>` に保存されます。有効化スイッチは `plugins.enabled.<プラグイン id>` です。

## フォームを超える UI

フォームで足りない場合（グラフ、操作ボタン、一覧）は、プラグインがフロントエンドコンポーネントを提供できます。[フロントエンドスロット](/ja/dev/plugins/frontend-slots) を参照してください。組み込みの `hardlink` の「既存ファイルをリンク」ボタンは `settings.section` のコンポーネントです。

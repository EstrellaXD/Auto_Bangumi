# 基本概念

## ディレクトリ構成とマニフェスト

```
config/plugins/local/my-plugin/     # ディレクトリ名はマニフェストの id と同じにします
├── plugin.toml
├── my_plugin/                      # パッケージ（または単一の my_plugin.py）。相対 import が使えます
│   └── __init__.py
├── web/                            # 任意：フロントエンドコンポーネント（「フロントエンドスロット」を参照）
└── vendor/                         # 任意：純 Python の依存（.so / .pyd / .dylib / .dll は禁止）
```

```toml
# plugin.toml
[plugin]
id = "my-plugin"              # 小文字・数字・ハイフン。core と local は予約済み
name = "My plugin"
version = "0.1.0"
sdk = ">=0.5,<1"              # 対応する ab_sdk のバージョン範囲
entry = "my_plugin:MyPlugin"  # モジュール:Plugin サブクラス（プラグインディレクトリからの相対）
description = "一文の説明"
authors = ["me"]
permissions = ["network"]     # ユーザーへの表示のみ。強制はされません
extension_points = ["notifier"]  # 任意：署名付きカタログの表示にだけ使います
```

プラグインは AB と同じプロセスで動作し、すべての権限を持ちます。`permissions` はユーザーへの宣言であり、サンドボックスではありません。`ab-plugin validate` はマニフェスト、SDK のバージョン範囲、エントリモジュール、フロントエンドのエントリファイルを検証します。

## Plugin と設定

- `Plugin[設定モデル]` を継承し、`config_model` を設定します。AB はモデルでユーザー設定を検証します。プラグインは `self.config` で型付きのインスタンスを受け取ります。WebUI で不正な値を保存しようとすると拒否されます（HTTP 422）。
- `async setup()` は読み込み後に一度、`async teardown()` はアンロード前に一度呼ばれます。設定が変わると、teardown の後でプラグインを作り直し、setup を呼びます。`setup()` が例外を送出すると、プラグインはエラー状態になります。
- フォームについては [設定フォーム](/ja/dev/plugins/config-forms) を参照してください。

`self.ctx` は、プラグインから見えるホストの機能のすべてです。

| 属性 | 説明 |
| --- | --- |
| `plugin_id` | プラグイン id |
| `config` | 検証済みの設定モデルのインスタンス（`config_model` がなければ `None`） |
| `log` | `plugin.<id>` のプレフィックス付き logger |
| `kv` | プラグイン専用の永続キーバリューストア（`get` / `set` / `delete`）。値は JSON にできるものに限ります |
| `data_dir` | `config/plugin-data/<id>/`。初回アクセス時に作成されます |
| `bus` | イベントバス：`publish(event)`、`subscribe(kind, handler)` |

プラグインでは `ab_sdk` だけを import してください。`module.*` は import しないでください。ホストの内部実装であり、いつでも変更される可能性があります。

## 3 種類の拡張宣言

| デコレーター | 用途 |
| --- | --- |
| `@provider(point, id=...)` | 拡張ポイントが定める実装を返すファクトリメソッド。`id` はユーザーが選ぶときの名前です |
| `@hook(point, priority=..., timeout=...)` | ホストが宣言した filter / transform 拡張ポイントに接続します。同じ拡張ポイントでは `priority` の昇順、同順位ならプラグイン id の順に実行します。ユーザーは `plugins.hook_order` で順序を指定できます |
| `@subscribe(kind, timeout=...)` | イベントを購読します。`"*"` は全イベントです。`timeout` で 1 イベントの処理時間の上限（既定 30 秒）を変更できます |

デコレーターは目印を付けるだけです。拡張ポイント名が間違っていると、プラグインの読み込みが失敗し、プラグイン一覧に理由が表示されます。黙って無視されることはありません。

- **filter フック**は `Verdict`（または `bool`）を返します。1 つでも拒否すると、そこで打ち切ります。
- **transform フック**は前のフックの結果を受け取り、新しい値を返します。`None` は変更なしです。フックが受け取るのは凍結されたスナップショットです。変更したコピーは `dataclasses.replace` で作って返します。

## 分離とサーキットブレーカー

- フック、イベントハンドラー、定期タスク、ルートハンドラーにはタイムアウトがあります。
- プラグインの例外はホストに影響しません。同じプラグインが 5 回連続で失敗すると、AB は自動的に無効にし、プラグイン一覧に理由を表示します。そのプラグインの設定を変更すると、再度読み込みを試みます。
- プラグインの戻り値は、ブレーカーの保護下で検証されます。型が違えば失敗として扱い、ホストの既定の動作に戻します。
- 例外：`RenameSkipped` は「入力または設定に問題がある」ことを表し、ブレーカーには数えません。

## テスト

`ab_sdk.testing` を使うと、AB を起動せずにプラグインを作成して動かせます。

```python
from ab_sdk.testing import create_plugin

def test_filter(tmp_path):
    plugin, ctx = create_plugin(MyPlugin, {"key": "k"}, data_dir=tmp_path)
    ...
    assert ctx.bus.published == []
```

`create_plugin` はホストと同じ規則で設定を検証し、プラグインを作成します（`setup` は呼びません）。`ctx.bus` はプラグインが発行したイベントを記録します。`await ctx.bus.deliver(event)` で、イベントをプラグイン自身の購読者に同期的に配信できます。

Provider 系の拡張ポイントには、SDK がコントラクトテストスイートを用意しています。スイートを継承して `create()` を実装すると、pytest がテストケースを収集します。

| スイート | 検査対象 |
| --- | --- |
| `DownloaderContract` | ダウンローダークライアント。`behavioral = True` でログインやトレント追加などの動作も検査します |
| `RenameStrategyContract` | リネーム方式：トレント内の相対パスを返す、拡張子を保つ、結果が決定的 |
| `NotifierContract` | 通知チャンネル：成功時は `True`、バックエンドが拒否したときは例外ではなく `False` |
| `SearchSiteContract` | 検索サイト：URL に `%s` が 1 つ、パーサーは `mikan` または `tmdb` |

```python
from ab_sdk.testing import RenameStrategyContract, create_plugin

class TestMyStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin(MyPlugin)
        return plugin.strategy()
```

テストケースは同期関数です（内部で `asyncio.run` を使います）。pytest-asyncio は不要です。

## pip パッケージとして公開する

パッケージの `pyproject.toml` に entry point を宣言し、**トップレベルのパッケージ内**に `plugin.toml` を置きます。

```toml
[project.entry-points."autobangumi.plugins"]
my-plugin = "my_plugin:MyPlugin"
```

pip でインストールしたプラグインも未署名です。「未署名プラグインを許可」をオンにする必要があります。Docker イメージには pip でインストールできません。その場合はローカルディレクトリを使い、依存を `vendor/` に入れてください。署名付きプラグインは [署名と配布](/ja/dev/plugins/signing) を参照してください。

# リネーム方式 (rename_strategy)

ダウンロードが完了すると、AB は設定「リネーム方式」（`plugins.slots.rename_strategy`）が選ぶ Provider を、トレント内の各本編と字幕に対して呼びます。ホストが持つのは `none`（元の名前のまま）だけです。`pn`、`advance`、`template` は組み込みプラグイン `rename` が提供します。プラグインが登録した `id` は、設定 → 作品管理設定 → リネーム方式の一覧に表示されます。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.rename import RenameInput, RenameSkipped, pad


class JellyfinStyle:
    def target_name(self, f: RenameInput) -> str:
        language = f".{f.language}" if f.kind == "subtitle" else ""
        if f.episode_type == "movie":
            return f"{f.bangumi_name}{language}{f.suffix}"
        if not f.bangumi_name:
            raise RenameSkipped("作品フォルダ名がありません")
        return f"{f.bangumi_name} - S{pad(f.season)}E{pad(f.episode)}{language}{f.suffix}"


class MyRename(Plugin):
    @provider(points.RENAME_STRATEGY, id="jellyfin-style")
    def jellyfin(self):
        return JellyfinStyle()
```

## RenameInput

凍結されたスナップショットです。

| フィールド | 説明 |
| --- | --- |
| `kind` | `media` または `subtitle`（字幕に別の方式はありません。`kind` で区別します） |
| `media_path` | トレント内の元の相対パス |
| `title` | ファイル名から解析したタイトル |
| `bangumi_name` | 保存ディレクトリの作品フォルダ名（映画は `Title (Year)`） |
| `season`、`episode` | シーズンと話数。`episode` には話数オフセットが適用済みです |
| `suffix` | ドット付きの拡張子。例：`.mkv` |
| `episode_type` | `episode`、`movie`、`special` |
| `language` | 字幕の言語。例：`zh`、`zh-tw` |
| `group` | 字幕グループ。`None` の場合があります |

`title` と `bangumi_name` は、ディスク上に既にあるファイル名やフォルダ名に由来します。それぞれ 1 つのパス要素です。AB は予約文字の除去を行いません。

## 戻り値とエラー

- トレント内の新しい相対パスを返します。通常はファイル名だけです。拡張子と字幕の言語は、方式自身が付けます。`f.media_path` を返すとリネームしません。
- `pad(n, width=2)` はゼロ埋めをし、小数部分を保ちます：`pad(9.5) == "09.5"`。総集編などの半話は小数部分を保つ必要があります。保たないと、同じシーズンの整数の話を上書きしてしまいます。
- `RenameSkipped(理由)` を送出すると、そのファイルは元の名前のままになり、トレントに「リネーム済み」タグは付かず、トレントごとに理由付きの `rename_skipped` 通知が 1 件送られます。問題を直せば、次の周期で自動的に再試行されます。これは入力または設定に問題があることを表し、ブレーカーには数えません。**失敗したときに別の命名方式へ切り替えないでください。**
- それ以外の例外、空文字列、文字列でない値：ファイルは同様に元の名前のままになり通知が送られます。また、失敗はブレーカーに数えられます。
- `target_name` は同期呼び出しで、タイムアウトがありません。中でネットワークやディスクの IO を行わないでください。
- 設定で選ばれた `id` が登録されていない場合（プラグインが無効、またはブレーカー作動中）は、AB がログを 1 行書き、`none` として動作します。

## テスト

```python
from ab_sdk.testing import RenameStrategyContract, create_plugin

class TestStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin(MyRename)
        return plugin.jellyfin()
```

スイートは次を検査します：空でない相対パス、`..` を含まない、拡張子が保たれる、結果が決定的。方式が一部の入力にしか対応しない場合は、`samples()` を上書きします。

例：`examples/plugins/template-rename`（独自フィルター付きのテンプレート）。

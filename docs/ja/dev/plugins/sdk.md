# SDK の入手

プラグイン SDK は PyPI に公開しません。4.0 の各 beta / 正式版の [GitHub Release](https://github.com/EstrellaXD/Auto_Bangumi/releases) に、プラグイン作者向けのファイルが 2 つ添付されます。

| ファイル | 内容 |
| --- | --- |
| `autobangumi_sdk-<SDK バージョン>-py3-none-any.whl` | `ab_sdk` パッケージと `ab-plugin` コマンド |
| `autobangumi-plugin-skill-<AB バージョン>.zip` | AI コーディングアシスタント向けのプラグイン開発 skill |

wheel のファイル名に入るのは SDK のバージョン（`ab_sdk.SDK_VERSION`、例えば `0.5.0`）で、AB のバージョンではありません。対象とする AB バージョンの Release から wheel をダウンロードしてください。両者の SDK バージョンが一致します。プラグインのマニフェストの `sdk` 範囲（例えば `">=0.5,<1"`）は、このバージョンを含む必要があります。

## wheel のインストール

wheel には Python 3.13 以上が必要です。依存は `pydantic`、`httpx`、`packaging` で、AutoBangumi 本体のインストールは不要です。

コマンドだけを使う場合は、グローバルなツールとしてインストールします。

```bash
uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
ab-plugin --help
```

プラグインを書いてテストを実行する場合は、wheel をプラグインプロジェクトの依存に追加します。

```bash
cd my-plugin
uv add ../autobangumi_sdk-0.5.0-py3-none-any.whl
uv run pytest
```

`uv add` は `pyproject.toml` の `[tool.uv.sources]` に wheel のローカルパスを記録します。`ab-plugin pack` は `pyproject.toml` と `uv.lock` をパッケージに含めないため、このパスはプラグインパッケージに入りません。`ab-plugin new` が作る `pyproject.toml` は `autobangumi-sdk` に依存していますが、入手元を指定していません。新しいひな形でも、先に一度 `uv add` を実行してください。

コントラクトテストには pytest が必要です。ひな形の `dev` 依存グループには pytest が入っています。オプション依存 `autobangumi-sdk[test]` をインストールすることもできます。

SDK を更新するときは、新しい Release の wheel をダウンロードし、`uv tool install --force <新しい wheel>` または `uv add <新しい wheel>` をもう一度実行します。

## AB のリポジトリで開発する

SDK のソースは `backend/src/ab_sdk`、パッケージ設定は `backend/sdk/pyproject.toml` にあります。`backend` の `dev` 依存グループが SDK を編集可能モードでインストールするため、リポジトリ内では wheel は不要です。

```bash
cd backend
uv sync --group dev
uv run ab-plugin validate ../examples/plugins/ntfy-notifier
```

wheel を自分でビルドする場合（CI と同じコマンド）：

```bash
uv build --wheel backend/sdk --out-dir sdk-dist
```

## プラグイン開発 skill

skill は Markdown の説明の集まりです。AI コーディングアシスタントはこれを読んで、AB プラグインを書き、テストし、パッケージ化します。zip には `autobangumi-plugin/` ディレクトリが入っています。

```
autobangumi-plugin/
├── SKILL.md                    # 作業手順、拡張ポイント一覧、よくある間違い
└── references/
    ├── extension-points.md     # 各拡張ポイントのシグネチャとフィールド
    ├── frontend.md             # フロントエンドスロット
    └── testing.md              # コントラクトテストと create_plugin
```

アシスタントの skills ディレクトリに展開します。Claude Code の場合、個人用の skills ディレクトリは `~/.claude/skills/` です。

```bash
unzip autobangumi-plugin-skill-<AB バージョン>.zip -d ~/.claude/skills/
```

ほかのアシスタントでは、それぞれの skills ディレクトリに置いてください。skill のソースはリポジトリの `skills/autobangumi-plugin/` です。

## CI でのビルド

`.github/workflows/build.yml` の `release` ジョブは、メンテナーがバージョンタグを push したときだけ実行されます。

1. `uv build --wheel backend/sdk --out-dir sdk-dist` で wheel をビルドします。バージョンは `ab_sdk.SDK_VERSION` から取ります。
2. `skills/autobangumi-plugin` を `autobangumi-plugin-skill-<AB バージョン>.zip` に圧縮します。
3. 2 つのファイルを、WebUI やオンライン更新バンドルなどと一緒に、そのバージョンの GitHub Release に添付します。beta（プレリリース）と正式版のどちらにも添付されます。

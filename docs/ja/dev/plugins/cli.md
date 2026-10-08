# コマンド ab-plugin

`ab-plugin` は `autobangumi-sdk` の wheel と一緒にインストールされます。依存は `ab_sdk` だけで、AutoBangumi 本体のインストールは不要です。

```bash
uv tool install ./autobangumi_sdk-0.5.0-py3-none-any.whl
# プロジェクト内の場合：uv add ./autobangumi_sdk-0.5.0-py3-none-any.whl
```

wheel は 4.0 beta / 正式版の GitHub Release の添付ファイルです。PyPI には公開しません。[SDK の入手](/ja/dev/plugins/sdk) を参照してください。コントラクトテストには pytest が必要です。`new` が作る `pyproject.toml` には `dev` 依存グループに pytest が入っています。自分で作ったプロジェクトでは `uv add --dev pytest`（または `autobangumi-sdk[test]` をインストール）を使います。

## new

```bash
ab-plugin new <id> [--kind rename|notifier|search] [--dir .]
```

`<id>/` ディレクトリを作成します。

```
<id>/
├── plugin.toml
├── <id のアンダースコア形>/__init__.py   # プラグインのコード
├── tests/test_contract.py                # ab_sdk.testing のスイートを継承
├── pyproject.toml                        # 開発専用。パッケージには含まれません
└── README.md
```

`id` に使えるのは小文字、数字、ハイフンだけです。ディレクトリが既にあると実行を拒否します。ダウンローダーのひな形はありません。ダウンローダーには実際のバックエンドが必要で、そのままコントラクトを通るひな形には意味がないためです。

生成される `pyproject.toml` は `autobangumi-sdk` に依存します。このパッケージは PyPI にないため、`uv run pytest` の前にプラグインディレクトリで一度 `uv add <wheel のパス>` を実行します。uv はこの依存にローカルの wheel を使うようになります。

## validate

```bash
ab-plugin validate [path]
```

マニフェストのフィールド、`sdk` の範囲に現在の SDK が含まれるか、エントリモジュールの有無、フロントエンドのエントリファイルの有無を検証します。ネイティブ拡張（`.so` / `.pyd` / `.dylib` / `.dll`）を含むディレクトリは拒否します。問題があると終了コードは 1 です。

## pack

```bash
ab-plugin pack [path] [-o dist]
```

検証してから `dist/<id>-<バージョン>.zip` を作成します。内容は zip のルートに置かれ、署名付きカタログのパッケージと同じ構成です。`tests/`、`pyproject.toml`、`uv.lock`、`dist/`、`.venv`、`.git`、`node_modules`、各種キャッシュ、`.pyc` は除外されます。ファイルの順序とタイムスタンプは固定なので、同じ内容からは同じ sha256 が得られます。

## dev

```bash
ab-plugin dev [path] [--config-dir config]
```

- 検証してから、プラグインディレクトリを `<config-dir>/plugins/local/<id>` にシンボリックリンクします。
- `--config-dir` の既定値はカレントディレクトリの `config` です。プラグインディレクトリで実行する場合は、AB の設定ディレクトリ（ソースから実行する場合は `backend/src/config`）を指定します。
- シンボリックリンクはプラグインディレクトリの絶対パスを指します。AB が同じパスでそこを開ける必要があります（ソースから実行する AB など）。AB を Docker で動かす場合は、プラグインディレクトリをコンテナの `config/plugins/local/<id>/` にコピーまたはマウントし、設定 → プラグイン で「未署名プラグインを許可」をオンにしてから有効にします。
- ホストの設定ファイル（`config_dev.json`、なければ `config.json`）に `plugins.dev_mode`、`plugins.allow_unsigned`、`plugins.enabled.<id>` を書き込みます。
- 設定ファイルがないと実行を拒否します。先に AutoBangumi を一度起動してください。
- 動作中の AB は設定ファイルを再読み込みしません。一度再起動してください。以後、`dev_mode` が 1 秒ごとにローカルプラグインのディレクトリを確認し、ファイルが変わるとそのプラグインをリロードします。読み込みに失敗したプラグインも監視されるので、ソースを直すと自動で復旧します。
- `dev_mode` が監視するのはローカルディレクトリだけです。pip パッケージは監視しません。新しく現れたプラグインディレクトリは、次の設定変更か再起動まで検出されません。

## 開発ループ

```bash
ab-plugin new my-notify --kind notifier
cd my-notify
uv add ../autobangumi_sdk-0.5.0-py3-none-any.whl   # 一度だけ
uv run pytest            # コントラクトテスト
ab-plugin dev . --config-dir /path/to/autobangumi/config   # リンクしてホットリロードを有効化。AB を一度再起動
# コードを変更 → AB が自動でリロード → WebUI で確認
ab-plugin pack .
```

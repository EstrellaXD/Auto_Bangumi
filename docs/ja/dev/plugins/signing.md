# 署名と配布

プラグインには 4 種類の入手元があり、それぞれ信頼レベルが異なります。

| 入手元 | 場所 | 署名 | 有効にする方法 |
| --- | --- | --- | --- |
| 組み込み | AB に同梱 | AB と一緒にリリース | 既定で利用可能 |
| 署名付きカタログ | `config/plugins/<id>/<バージョン>/` | ed25519 署名。AB が検証 | インストール API を呼ぶ。インストールすると有効になります |
| ローカルディレクトリ | `config/plugins/local/<id>/` | なし | 「未署名プラグインを許可」をオンにしてから有効化 |
| pip パッケージ | entry point `autobangumi.plugins` | なし | 同上 |

同じ id のプラグインがある場合の優先順位は、組み込み > 署名付きカタログ > ローカル > pip です。未署名プラグインは、ユーザーが設定 → プラグインで先に「未署名プラグインを許可」をオンにしてから有効にします。オフの間、AB は未署名プラグインのコードを一切実行しません。

## 署名付きカタログ

AB は GitHub release `plugins` から `catalog.json` をダウンロードします。カタログの内容は次のとおりです。

```json
{
  "schema": 2,
  "plugins": [
    {
      "id": "ntfy-notifier",
      "name": "ntfy 通知",
      "version": "0.1.0",
      "kind": "plugin",
      "extension_points": ["notifier"],
      "sdk": ">=0.5,<1",
      "min_ab_version": "4.0.0-beta.1",
      "description": "…",
      "asset": "ntfy-notifier-0.1.0.zip",
      "sha256": "…"
    }
  ]
}
```

`catalog.json` と各 zip には、同名の `.sig` ファイルが付きます。ファイル全体のバイト列に対する ed25519 署名を base64 で符号化したものです。公開鍵は AB イメージに含まれます。オンライン更新と同じ鍵です。

インストール時、AB は次の順に検査します。

1. `catalog.json` の署名。
2. zip の sha256 と署名。未署名のパッケージと署名が不正なパッケージは拒否します。
3. 展開時の zip-slip 対策。展開先の外に出るパスは拒否します。
4. マニフェストは `ab-plugin validate` と同じ検査に通る必要があります。マニフェストの `id` と `version` はカタログのエントリと一致しなければなりません。`sdk` の範囲に現在の SDK が含まれ、AB のバージョンが `min_ab_version` 以上である必要があります。
5. id は予約 id（`core`、`local`）であってはならず、組み込みプラグインと同名であってもいけません。

検査に通ると、AB はプラグインを `config/plugins/<id>/<バージョン>/` に展開し、そのバージョンを指す `installed.json` を書き込み、プラグインを読み込んで有効にします。アンインストールで削除されるのは `installed.json` のあるディレクトリだけです。ユーザーのローカルプラグインは削除されません。

カタログのプラグインが依存できるのは、標準ライブラリと AB に既にあるパッケージだけです。AB は pip を実行しません。サードパーティの純 Python ライブラリは `vendor/` に入れてください。

::: tip WebUI からインストールする
設定 → プラグインの「Plugin catalog」（プラグインカタログ）で「Browse catalog」を選ぶと、カタログのプラグインをインストール・更新できます。カタログからインストールしたプラグインのカードには「Uninstall」ボタンがあります。組み込み、ローカル、pip のプラグインにはありません。
:::

API：

| リクエスト | 説明 |
| --- | --- |
| `GET /api/v1/plugins/catalog` | カタログのエントリと、この環境にインストール済みのバージョン。カタログに到達できないと 502 |
| `POST /api/v1/plugins/{id}/install` | インストールして有効化 |
| `DELETE /api/v1/plugins/{id}` | アンインストール |

::: warning 予約パス
`/plugins/{id}/install` と `/plugins/catalog` はホストが使います。プラグイン自身の `api_router` では、`install`、`catalog`、`web` をルートのパスに使えません。
:::

## プラグインを公開する

カタログを公開できるのは、署名用の秘密鍵を持つメンテナーだけです。手順は次のとおりです。

1. 作者が `ab-plugin pack .` を実行し、zip を作ります。
2. 作者が zip とソースの場所を添えて GitHub issue を作り、掲載を依頼します。
3. メンテナーがソースを確認し、1 つ以上の zip に対して次のコマンドを実行します。

   ```bash
   uv run --no-project --with cryptography python scripts/build_plugin_catalog.py \
       --key ~/.autobangumi/update-signing-key.pem --min-ab 4.0.0-beta.1 \
       --out release-assets dist/*.zip
   ```

   スクリプトは `catalog.json`、各 zip、およびその `.sig` を出力します。`--min-ab` に `4.0.0` を指定しないでください。semver では `4.0.0-beta.N` は `4.0.0` より低いため、4.0 beta のユーザーがインストールできなくなります。
4. メンテナーがディレクトリ全体を release `plugins` にアップロードします（古いファイルは上書きします）。

ユーザーは `GET /api/v1/plugins/catalog` で新しいバージョンを確認できます。

## SDK の公開

SDK は、4.0 beta / 正式版の GitHub Release の添付ファイルとして wheel で配布します。CI が `uv build --wheel backend/sdk` でビルドします。同じ release に `autobangumi-plugin-skill-<バージョン>.zip` も添付されます。AI コーディングアシスタント向けのプラグイン開発 skill です。アシスタントの skills ディレクトリに展開してください。

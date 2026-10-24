# フロントエンドスロット

プラグインは WebUI の決まった場所に、独自の UI をマウントできます。UI は標準の Web Component（custom element）です。ES モジュールが要素を定義し、AB が要素を作成して `host` と `context` を渡します。フロントエンドフレームワークは不要です。Vue や Lit などを使いたい場合は、モジュールにバンドルしてください。

## マニフェスト

```toml
[[plugin.ui]]
slot = "bangumi.detail.tab"
element = "ab-plugin-manual-pick"
entry = "web/index.js"
title = { zh-CN = "手动选种", en-US = "Manual pick" }
```

- `slot`：スロット。下の表を参照してください。
- `element`：custom element 名。`ab-plugin-<プラグイン id>` か、`ab-plugin-<プラグイン id>-` で始まる名前にします。この名前空間はプラグインのものです。他のプラグインの要素名は定義できません。
- `entry`：要素を定義する ES モジュール。`web/` の下に置きます。
- `title`：言語ごとのタイトル（1 言語以上）。タブ名、ページタイトル、設定セクション名に使われます。

マニフェストが不正だと、AB はプラグイン全体を拒否します。`ab-plugin validate` はエントリファイルの有無を検査します。

## スロット

| `slot` | 位置 | `context` |
| --- | --- | --- |
| `settings.section` | 設定ページのセクション一覧の末尾。サイドバーと検索で見えます | `{}` |
| `bangumi.detail.tab` | 作品編集ダイアログのタブ（プラグインのタブがあるときだけセグメントコントロールを表示） | `{ bangumiId }` |
| `bangumi.card.action` | 作品カードのタイトル下の操作バー | `{ bangumiId }` |
| `page` | サイドバーの項目とルート `/plugins/<id>`。ページタイトルはマニフェストのタイトル | `{}` |
| `dashboard.widget` | 作品一覧ページ上部のグリッド | `{}` |

モバイルの下部ナビゲーションにはプラグインページの項目がありません。スマートフォンではアドレスを直接開いてください。

## コンポーネントと AbHost

AB は、要素を挿入する前に `host` と `context` プロパティを設定します。`connectedCallback` の中でそのまま使えます。

```js
class MyWidget extends HTMLElement {
  async connectedCallback() {
    const root = this.attachShadow({ mode: 'open' });
    root.innerHTML = `<button>${this.host.i18n.locale}</button>`;
    root.querySelector('button').onclick = async () => {
      const data = await this.host.api.get('stats');      // /api/v1/plugins/<id>/stats
      this.host.toast(JSON.stringify(data));
    };
    this.off = this.host.events.on('my-plugin.changed', () => this.refresh());
  }
  disconnectedCallback() { this.off?.(); }
}
customElements.define('ab-plugin-my-plugin', MyWidget);
```

| メンバー | 説明 |
| --- | --- |
| `host.pluginId` | プラグイン id |
| `host.api.get/post/put/delete` | ログイン状態付きのリクエスト。解析済みの JSON を返し、2xx 以外では reject します。`/` で始まらないパスは `/api/v1/plugins/<id>/` からの相対です。`/api/v1/` で始まるパスはホストの API で、GET のみ許可されます（公開の読み取り専用。他のプラグインの GET ルートを含む） |
| `host.i18n.locale` | 現在の言語。例：`zh-CN`、`en-US` |
| `host.i18n.t(key, params?)` | ホストの文言を翻訳します。見つからないときは key を返します |
| `host.theme.mode` / `host.theme.tokens` | 現在のライト / ダークモードと `--ab-*` 変数の値。テーマに合わせてリアルタイムに変わります |
| `host.toast(message, kind?)` | メッセージを表示します（`info` または `error`） |
| `host.events.on(kind, callback)` | イベントバスのイベントを購読します。コールバックはイベントのフィールドを受け取ります。購読解除関数を返します。コンポーネントがアンマウントされると AB も購読を解除します |

プラグインの範囲を出るパス（`..`、`//host`、完全な URL）は拒否されます。これは誤用を防ぐ仕組みであり、セキュリティ境界ではありません。コンポーネントはメインサイトと同一オリジンなので、プラグインはすべての権限を持ちます。リクエストは既定でエラーメッセージを表示しません。エラーの見せ方はプラグインが決めます。

## スタイル

AB はコンポーネントを Shadow DOM のラッパーに入れ、グローバルスタイルから分離します。ラッパーにはテーマ変数（`--ab-color-primary`、`--ab-color-surface`、`--ab-color-text`、`--ab-radius-sm`、`--ab-font-mono` など。全一覧は `@autobangumi/plugin-ui` の `tokens.css`）が注入されます。ビルドしないコンポーネントは `var(--ab-…)` をそのまま使えます。ライト / ダークは自動で切り替わります。

## ビルドテンプレート

ネイティブモジュールを手書きしたくない場合は、ワークスペースパッケージ `@autobangumi/plugin-ui`（`webui/packages/plugin-ui/`、npm には公開しません）を使います。

- `src/index.ts`：`AbHost`、`AbPluginElement`、`AbSlotContext` などの型。
- `tokens.css`：テーマ変数。
- `template/`：Vite のライブラリモードのテンプレート。自己完結した単一の ES モジュールを `../web/index.js` に出力し、`tokens.css` を Shadow DOM にインライン化します。プラグインにコピーして、要素名を変えて使います。

## 制約

- **CSP**：AB のページには `Content-Security-Policy: script-src 'self'` が付きます。モジュールは AB のアドレス（`/api/v1/plugins/<id>/web/...`）から読み込む必要があります。インラインスクリプト、`eval`、サードパーティ CDN のスクリプトは使えません。画像、スタイル、ネットワークリクエストは制限されません。
- **静的ファイル**：`web/` ディレクトリは `GET /api/v1/plugins/<id>/web/<パス>` で配信されます。ログインが必要で、有効なプラグインだけを配信し、ディレクトリの外に出るパスとシンボリックリンクは拒否します。このため、プラグインの `api_router` は `web/` のプレフィックスを使えません。
- **エラー境界**：モジュールの import 失敗、未定義の要素、コンポーネント内の未捕捉エラーがあると、そのプラグインのスロットだけが「プラグインコンポーネントの読み込みに失敗」と表示します。ページと他のプラグインには影響しません。再試行ボタンはありません。ページを開き直すと再度 import します。
- **キャッシュ**：モジュールには `Cache-Control: no-cache` が付きます。プラグインの更新後は、ブラウザが ETag で再検証します。

動作する完全な例は `examples/plugins/manual-pick/` です。詳細ページのタブで、ホストの読み取り専用 API でトレントを一覧し、プラグイン自身のルートで選択を保存し、別の場所で選択されたときは `host.events.on` で更新します。

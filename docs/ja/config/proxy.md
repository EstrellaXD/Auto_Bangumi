# プロキシとリバースプロキシ

## プロキシ

![proxy](/image/config/proxy.png){width=500}{class=ab-shadow-card}

<br/>

ABはネットワーク問題を解決するためにHTTPおよびSOCKS5プロキシをサポートしています。

- **有効**：プロキシを有効にするかどうか。
- **タイプ**はプロキシタイプです。
- **ホスト**はプロキシアドレスです。
- **ポート**はプロキシポートです。

::: tip
**SOCKS5**モードでは、ユーザー名とパスワードが必要です。
:::

## `config.json`設定オプション

設定ファイルの対応するオプションは以下のとおりです：

設定セクション：`proxy`

| パラメータ | 説明             | タイプ    | WebUIオプション   | デフォルト |
|-----------|-----------------|---------|-----------------|-----------|
| enable    | プロキシ有効     | ブール値 | プロキシ         | false     |
| type      | プロキシタイプ   | 文字列   | プロキシタイプ   | http      |
| host      | プロキシアドレス | 文字列   | プロキシアドレス  |           |
| port      | プロキシポート   | 整数     | プロキシポート    |           |
| username  | プロキシユーザー名 | 文字列   | プロキシユーザー名 |          |
| password  | プロキシパスワード | 文字列   | プロキシパスワード |          |

## リバースプロキシ

- Mikan Projectの代替ドメイン`mikanime.tv`を使用して、RSS購読URLの`mikanani.me`を置き換えます。
- Cloudflare Workerをリバースプロキシとして使用し、RSSフィード内のすべての`mikanani.me`ドメインを置き換えます。

## Cloudflare Workers

他のサービスのブロックをバイパスするために使用されるアプローチに基づいて、Cloudflare Workersを使用してリバースプロキシを設定できます。ドメインの登録とCloudflareへのバインド方法は、このガイドの範囲外です。Workersに以下のコードを追加して、独自のドメインを使用してMikan Projectにアクセスし、RSSリンクからトレントをダウンロードします：

```js
const TELEGRAPH_URL = 'https://mikanani.me';
const MY_DOMAIN = 'https://yourdomain.com'

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);
  url.host = TELEGRAPH_URL.replace(/^https?:\/\//, '');

  const modifiedRequest = new Request(url.toString(), {
    headers: request.headers,
    method: request.method,
    body: request.body,
    redirect: 'manual'
  });

  const response = await fetch(modifiedRequest);
  const contentType = response.headers.get('Content-Type') || '';

  // コンテンツタイプがRSSの場合のみ置換を実行
  if (contentType.includes('application/xml')) {
    const text = await response.text();
    const replacedText = text.replace(/https?:\/\/mikanani\.me/g, MY_DOMAIN);
    const modifiedResponse = new Response(replacedText, response);

    // CORSヘッダーを追加
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');

    return modifiedResponse;
  } else {
    const modifiedResponse = new Response(response.body, response);

    // CORSヘッダーを追加
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');

    return modifiedResponse;
  }
}
```

# ネットワーク問題

## Mikan Projectに接続できない

Mikan Projectのメインサイト（`https://mikanani.me`）は一部の地域でブロックされている可能性があるため、ABは接続に失敗することがあります。以下の解決策を使用してください：

- [Mikan Projectの代替ドメインを使用](#mikan-projectの代替ドメイン)
- [プロキシを使用](#プロキシの設定)
- [Cloudflare Workerリバースプロキシを使用](#cloudflare-workersリバースプロキシ)

### Mikan Projectの代替ドメイン

Mikan Projectには新しいドメイン`https://mikanime.tv`があります。プロキシを有効にせずに、このドメインをABで使用してください。

以下が表示される場合：
```
DNS/Connect ERROR
```

- ネットワーク接続を確認してください。問題がない場合は、DNS解決を確認してください。
- ABに`dns=8.8.8.8`を追加してください。Hostネットワークモードを使用している場合、これは無視できます。

プロキシを使用している場合、正しい設定であればこのエラーは通常発生しません。

### プロキシの設定

::: tip
AB 3.1以降、ABはRSS更新と通知を自分で処理するため、ABでプロキシを設定するだけで十分です。
:::

ABにはプロキシ設定が組み込まれています。プロキシを設定するには、[プロキシ設定](/ja/config/proxy)の指示に従ってHTTPまたはSOCKSプロキシを正しく設定してください。これでアクセス問題が解決されます。

**3.1より前のバージョンでは、qBittorrentのプロキシ設定も必要です**

QBで以下のようにプロキシを設定してください（SOCKSも同様のアプローチ）：

<img width="483" alt="image" src="https://user-images.githubusercontent.com/33726646/233681562-cca3957a-a5de-40e2-8fb3-4cc7f57cc139.png">


### Cloudflare Workersリバースプロキシ

Cloudflare Workersを介したリバースプロキシアプローチも使用できます。ドメインの設定とCloudflareへのバインドは、このガイドの範囲外です。
Workersに以下のコードを追加して、独自のドメインを使用してMikan Projectにアクセスし、RSSリンクからトレントをダウンロードします：

```javascript
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

設定が完了したら、**RSSを追加する**際に`https://mikanani.me`をあなたのドメインに置き換えてください。

## qBittorrentに接続できない

まず、ABの**ダウンローダーアドレス**パラメータが正しいか確認してください。
- ABとQBが同じDockerネットワーク上にある場合、コンテナ名を使用したアドレス指定を試してください。例：`http://qbittorrent:8080`。
- ABとQBが同じDockerサーバー上にある場合、Dockerゲートウェイアドレスを使用してみてください。例：`http://172.17.0.1:8080`。
- ABのネットワークモードが`host`でない場合、QBへのアクセスに`127.0.0.1`を使用しないでください。

Docker内のコンテナが相互にアクセスできない場合は、QBのネットワーク接続設定でQBとAB間のネットワークリンクを設定してください。qBittorrentがHTTPSを使用する場合は、**ダウンローダーアドレス**に`https://`プレフィックスを追加してください。

# 网络问题

## 无法连接蜜柑计划

由于蜜柑计划本站: `https://mikanani.me` 目前被 GFW 封锁，因此可能会导致 AB 无法正确连接蜜柑计划的情况，建议使用如下方法解决。

- [使用蜜柑计划国内域名](#蜜柑计划国内域名)
- [使用代理](#配置代理)
- [使用 CloudFlare Worker 进行反代](#cloudflare-workers-反代)

### 蜜柑计划国内域名

蜜柑计划更新了新的域名 `https://mikanime.tv`，请在不打开代理的情况下配合 AB 使用。

如果出现  
```
DNS/Connect ERROR
```

- 请检查网络连接，如果网络连接正常，请检查 DNS 解析。
- 可以给 AB 添加一个 `dns=8.8.8.8`，如果是 HOST 模式可以忽略。

如果你是用代理，一般配置正确不会出现类似错误。

### 配置代理

::: tip
在 AB 3.1 中，AB 已经接管了 RSS 更新以及推送，因此在使用代理的时候，只需要在 AB 中配置代理。
:::

AB 中自带了代理配置，如果要配置代理请按照 [配置代理](../config/proxy) 中的方式正确配置 HTTP 或者 Socks 代理。配置完成可以规避墙的问题。

**3.1 以前版本需要对 QB 进行代理配置**

请按照如下截图对 QB 中进行代理设置 （Socks 同理）

<img width="483" alt="image" src="https://user-images.githubusercontent.com/33726646/233681562-cca3957a-a5de-40e2-8fb3-4cc7f57cc139.png">


### CloudFlare Workers 反代

根据 OpenAI 被墙的经验，我们也可以通过反向代理的方式解决。具体如何申请域名绑定 CloudFlare 在此不再赘述。
在 Workers 中添加如下代码即可以用你自己的域名访问蜜柑计划并且解析下载 RSS 链接中的种子。

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

  // 如果内容类型是 RSS，才进行替换操作
  if (contentType.includes('application/xml')) {
    const text = await response.text();
    const replacedText = text.replace(/https?:\/\/mikanani\.me/g, MY_DOMAIN);
    const modifiedResponse = new Response(replacedText, response);

    // 添加允许跨域访问的响应头
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');

    return modifiedResponse;
  } else {
    const modifiedResponse = new Response(response.body, response);

    // 添加允许跨域访问的响应头
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');

    return modifiedResponse;
  }
}
```

完成上述配置之后，使用你的域名替换 `https://mikanani.me` **添加 RSS** 即可。

## 无法连接到 qBittorrent

首先，检查 AB 中的 **下载器地址** 参数是否正确。
- 如果你的 AB 和 QB 在同一个 Docker 网络中，可以尝试使用容器名称进行寻址，如：`http://qbittorrent:8080`。
- 如果你的 AB 和 QB 在同一个 Docker 服务器中，可以尝试使用 Docker 网关地址进行访问，如：`http://172.17.0.1:8080`。
- 如果 AB 网络模式不是 `host` 请不要使用 `127.0.0.1` 来访问 QB

在 Docker 中不同容器中无法互相访问，可以在 QB 的网络连接的链接中，设定链接 AB， 如果 qBittorrent 使用 HTTPS 模式，请在 **下载器地址** 参数中添加 `https://` 前缀。


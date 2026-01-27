# 网络问题

## 无法连接到 Mikan Project

由于 Mikan Project 主站（`https://mikanani.me`）在某些地区可能被屏蔽，AB 可能无法连接。请使用以下解决方案：

- [使用 Mikan Project 备用域名](#mikan-project-备用域名)
- [使用代理](#配置代理)
- [使用 Cloudflare Worker 反向代理](#cloudflare-workers-反向代理)

### Mikan Project 备用域名

Mikan Project 有一个新域名 `https://mikanime.tv`。使用此域名配合 AB，无需启用代理。

如果您看到：
```
DNS/Connect ERROR
```

- 请检查您的网络连接。如果网络正常，请检查 DNS 解析。
- 在 AB 中添加 `dns=8.8.8.8`。如果使用 Host 网络模式，可以忽略此项。

如果您使用代理，正确配置后通常不会出现此错误。

### 配置代理

::: tip
在 AB 3.1+ 中，AB 自己处理 RSS 更新和通知，因此您只需要在 AB 中配置代理。
:::

AB 有内置的代理配置。要配置代理，请按照[代理设置](../config/proxy)中的说明正确设置 HTTP 或 SOCKS 代理。这可以解决访问问题。

**对于 3.1 之前的版本，还需要配置 qBittorrent 代理**

如下图所示在 QB 中配置代理（SOCKS 方法相同）：

<img width="483" alt="image" src="https://user-images.githubusercontent.com/33726646/233681562-cca3957a-a5de-40e2-8fb3-4cc7f57cc139.png">


### Cloudflare Workers 反向代理

您也可以通过 Cloudflare Workers 使用反向代理方式。设置域名并绑定到 Cloudflare 超出了本指南的范围。
在 Workers 中添加以下代码，即可使用您自己的域名访问 Mikan Project 并从 RSS 链接下载种子：

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

  // Only perform replacement if content type is RSS
  if (contentType.includes('application/xml')) {
    const text = await response.text();
    const replacedText = text.replace(/https?:\/\/mikanani\.me/g, MY_DOMAIN);
    const modifiedResponse = new Response(replacedText, response);

    // Add CORS headers
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');

    return modifiedResponse;
  } else {
    const modifiedResponse = new Response(response.body, response);

    // Add CORS headers
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');

    return modifiedResponse;
  }
}
```

完成配置后，**添加 RSS** 时将 `https://mikanani.me` 替换为您的域名。

## 无法连接到 qBittorrent

首先，检查 AB 中的 **下载器地址** 参数是否正确。
- 如果 AB 和 QB 在同一个 Docker 网络中，请尝试使用容器名称进行寻址，例如 `http://qbittorrent:8080`。
- 如果 AB 和 QB 在同一台 Docker 服务器上，请尝试使用 Docker 网关地址，例如 `http://172.17.0.1:8080`。
- 如果 AB 的网络模式不是 `host`，请不要使用 `127.0.0.1` 访问 QB。

如果 Docker 中的容器无法相互访问，请在 QB 的网络连接设置中设置 QB 和 AB 之间的网络链接。如果 qBittorrent 使用 HTTPS，请在 **下载器地址** 前添加 `https://` 前缀。

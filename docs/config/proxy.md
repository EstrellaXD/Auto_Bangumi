# 代理与反向代理

## 代理

![proxy](../image/config/proxy.png){width=500}{class=ab-shadow-card}

<br/>

AB 支持 HTTP 和 SOCKS5 代理，以帮助解决网络问题。

- **启用**：是否启用代理。
- **类型** 为代理类型。
- **地址** 为代理地址。
- **端口** 为代理端口。

::: tip
在 **SOCKS5** 模式下，需要填写用户名和密码。
:::

## `config.json` 配置选项

配置文件中的对应选项如下：

配置节：`proxy`

| 参数     | 说明       | 类型    | WebUI 选项   | 默认值 |
|----------|------------|---------|--------------|--------|
| enable   | 启用代理   | 布尔值  | 代理         | false  |
| type     | 代理类型   | 字符串  | 代理类型     | http   |
| host     | 代理地址   | 字符串  | 代理地址     |        |
| port     | 代理端口   | 整数    | 代理端口     |        |
| username | 代理用户名 | 字符串  | 代理用户名   |        |
| password | 代理密码   | 字符串  | 代理密码     |        |

## 反向代理

- 使用 Mikan Project 备用域名 `mikanime.tv` 替换 RSS 订阅链接中的 `mikanani.me`。
- 使用 Cloudflare Worker 作为反向代理，替换 RSS 订阅中所有的 `mikanani.me` 域名。

## Cloudflare Workers

参考绕过其他服务封锁的方法，您可以使用 Cloudflare Workers 搭建反向代理。如何注册域名并绑定到 Cloudflare 不在本指南范围内。在 Workers 中添加以下代码，即可使用自己的域名访问 Mikan Project 并从 RSS 链接下载种子：

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

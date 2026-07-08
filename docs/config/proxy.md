# 代理与反向代理

## 代理

![proxy](/image/config/proxy.png){width=700}{class=ab-shadow-card}

AB 支持 HTTP、HTTPS 和 SOCKS5 代理，用于访问 RSS、搜索源、TMDB、Bangumi、LLM provider 等外部服务。

- **启用**：是否启用代理。
- **类型**：`http`、`https` 或 `socks5`。
- **地址 / 端口**：代理服务地址与端口。
- **用户名 / 密码**：代理需要认证时填写。配置值支持使用环境变量引用。

修改代理设置后，需要点击底部 **保存并重启**。

## `config.json` 配置选项

配置节：`proxy`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `enable` | 启用代理 | 布尔值 | 启用 | `false` |
| `type` | 代理类型 | 字符串 | 类型 | `http` |
| `host` | 代理地址 | 字符串 | 地址 | `""` |
| `port` | 代理端口 | 整数 | 端口 | `0` |
| `username` | 代理用户名 | 字符串 | 用户名 | `""` |
| `password` | 代理密码 | 字符串 | 密码 | `""` |

## 反向代理

如果 Mikan Project 主域名无法访问，可以：

- 使用备用域名 `mikanime.tv` 替换 RSS 订阅链接中的 `mikanani.me`。
- 使用 Cloudflare Workers 等服务搭建反向代理，并替换 RSS 中的域名。

## Cloudflare Workers 示例

```js
const TELEGRAPH_URL = 'https://mikanani.me';
const MY_DOMAIN = 'https://yourdomain.com';

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  url.host = TELEGRAPH_URL.replace(/^https?:\/\//, '');

  const modifiedRequest = new Request(url.toString(), {
    headers: request.headers,
    method: request.method,
    body: request.body,
    redirect: 'manual',
  });

  const response = await fetch(modifiedRequest);
  const contentType = response.headers.get('Content-Type') || '';

  if (contentType.includes('application/xml')) {
    const text = await response.text();
    const replacedText = text.replace(/https?:\/\/mikanani\.me/g, MY_DOMAIN);
    const modifiedResponse = new Response(replacedText, response);
    modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');
    return modifiedResponse;
  }

  const modifiedResponse = new Response(response.body, response);
  modifiedResponse.headers.set('Access-Control-Allow-Origin', '*');
  return modifiedResponse;
}
```

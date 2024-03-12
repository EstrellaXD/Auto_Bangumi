# 代理和反向代理

## 代理

![proxy](../image/config/proxy.png){width=500}{class=ab-shadow-card}

<br/>

AB 支持 HTTP 代理和 SOCKS5 代理，通过设置代理可以解决一些网络问题。

- **Enable**: 是否启用代理。
- **Type** 为代理类型。
- **Host** 为代理地址。
- **Port** 为代理端口。

::: tip
在 **Socks5** 模式下，需要添加用户名和密码。
:::

## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`proxy`

| 参数名      | 参数说明   | 参数类型 | WebUI 对应选项 | 默认值   |
|----------|--------|------|------------|-------|
| enable   | 是否启用代理 | 布尔值  | 代理         | false |
| type     | 代理类型   | 字符串  | 代理类型       | http  |
| host     | 代理地址   | 字符串  | 代理地址       |
| port     | 代理端口   | 整数   | 代理端口       |
| username | 代理用户名  | 字符串  | 代理用户名      |
| password | 代理密码   | 字符串  | 代理密码       |

## 反向代理

- 使用蜜柑计划的新域名 `mikanime.tv` 替换rss订阅中 `mikanani.me` 部分
- 使用 CloudFlare Worker 进行反代，并且替换 RSS 中所有的 `mikanani.me` 域名。

## CloudFlare Workers

根据 OpenAI 被墙的经验，我们也可以通过反向代理的方式解决。具体如何申请域名绑定 CloudFlare 在此不再赘述。在 Workers 中添加如下代码即可以用你自己的域名访问蜜柑计划并且解析下载 RSS 链接中的种子。

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

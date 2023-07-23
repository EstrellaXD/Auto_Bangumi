# Mikan 网络问题的应对方法

由于蜜柑计划本站: `https://mikanani.me` 目前被 GFW 封锁，因此可能会导致 AB 无法正确连接蜜柑计划的情况，建议使用如下方法解决。

- [使用蜜柑计划国内域名](#蜜柑计划国内域名)
- [使用代理](#代理)
- [使用 CloudFlare Worker 进行反代](#cloudflare-workers)

## 蜜柑计划国内域名

- 蜜柑计划更新了新的域名 `https://mikanime.tv`，请在不打开代理的情况下配合 AB 使用。


## 配置代理

1. AB 中自带了代理配置，如果要配置代理请按照 [配置代理](../config/proxy) 中的方式正确配置 HTTP 或者 Socks 代理。配置完成可以规避墙的问题。
2. QB 中也需要配置代理，请按照如下截图对 QB 中进行代理设置 （Socks 同理）
<img width="483" alt="image" src="https://user-images.githubusercontent.com/33726646/233681562-cca3957a-a5de-40e2-8fb3-4cc7f57cc139.png">

3. 在 2.6 版本更新中 AB 额外提供了两种解决被墙的方案。

- 可以在 WebUI 中的 `源站链接` 中修改为自己反代过的 URL
- 使用代理之后可以使用 AB 自身作为反代节点。

具体可以看[配置代理](../config/proxy)中的说明。

## CloudFlare Workers

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

完成上述配置之后，将你的域名填入 AB 的 **源站链接｜Custom URL** 中即可。
# Network Issues

## Cannot Connect to Mikan Project

Since the main Mikan Project site (`https://mikanani.me`) may be blocked in some regions, AB may fail to connect. Use the following solutions:

- [Use Mikan Project alternative domain](#mikan-project-alternative-domain)
- [Use a proxy](#configuring-a-proxy)
- [Use a Cloudflare Worker reverse proxy](#cloudflare-workers-reverse-proxy)

### Mikan Project Alternative Domain

Mikan Project has a new domain `https://mikanime.tv`. Use this domain with AB without enabling a proxy.

If you see:
```
DNS/Connect ERROR
```

- Check your network connection. If it's fine, check DNS resolution.
- Add `dns=8.8.8.8` to AB. If using Host network mode, this can be ignored.

If you're using a proxy, this error typically won't occur with correct configuration.

### Configuring a Proxy

::: tip
In AB 3.1+, AB handles RSS updates and notifications itself, so you only need to configure the proxy in AB.
:::

AB has built-in proxy configuration. To configure a proxy, follow the instructions in [Proxy Settings](../config/proxy) to set up HTTP or SOCKS proxy correctly. This resolves access issues.

**For versions before 3.1, qBittorrent proxy configuration is also needed**

Configure the proxy in QB as shown below (same approach for SOCKS):

<img width="483" alt="image" src="https://user-images.githubusercontent.com/33726646/233681562-cca3957a-a5de-40e2-8fb3-4cc7f57cc139.png">


### Cloudflare Workers Reverse Proxy

You can also use a reverse proxy approach via Cloudflare Workers. Setting up a domain and binding it to Cloudflare is beyond the scope of this guide.
Add the following code in Workers to use your own domain to access Mikan Project and download torrents from RSS links:

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

After completing the configuration, replace `https://mikanani.me` with your domain when **adding RSS**.

## Cannot Connect to qBittorrent

First, check if the **downloader address** parameter in AB is correct.
- If AB and QB are on the same Docker network, try using the container name for addressing, e.g., `http://qbittorrent:8080`.
- If AB and QB are on the same Docker server, try using the Docker gateway address, e.g., `http://172.17.0.1:8080`.
- If AB's network mode is not `host`, do not use `127.0.0.1` to access QB.

If containers in Docker cannot access each other, set up a network link between QB and AB in QB's network connection settings. If qBittorrent uses HTTPS, add the `https://` prefix to the **downloader address**.

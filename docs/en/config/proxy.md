# Proxy And Reverse Proxy

## Proxy

![proxy](/image/config/proxy.png){width=700}{class=ab-shadow-card}

AutoBangumi supports HTTP, HTTPS and SOCKS5 proxies for RSS, search providers, TMDB, Bangumi, LLM providers and other outbound requests.

- **Enable**: enables the proxy.
- **Type**: `http`, `https` or `socks5`.
- **Host / Port**: proxy address and port.
- **Username / Password**: fill them when your proxy requires authentication. Values can reference environment variables.

Click **Save & restart** after changing proxy settings.

## `config.json`

Section: `proxy`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `enable` | Enable proxy | boolean | Enable | `false` |
| `type` | Proxy type | string | Type | `http` |
| `host` | Proxy host | string | Host | `""` |
| `port` | Proxy port | integer | Port | `0` |
| `username` | Proxy username | string | Username | `""` |
| `password` | Proxy password | string | Password | `""` |

## Reverse Proxy

If Mikan Project is unreachable, you can replace `mikanani.me` with the alternate domain `mikanime.tv`, or deploy a reverse proxy such as Cloudflare Workers and rewrite RSS URLs through your own domain.

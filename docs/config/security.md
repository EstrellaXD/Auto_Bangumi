# 安全设置

![security](/image/config/security.png){width=700}{class=ab-shadow-card}

安全设置用于限制登录入口和 MCP 服务访问。修改后需要点击底部 **保存并重启**。

- **登录 IP 白名单**：允许访问登录接口的 IPv4/IPv6 CIDR。为空表示允许所有 IP。
- **登录 API 令牌**：允许通过 `Authorization: Bearer <token>` 访问受保护 API。
- **MCP IP 白名单**：允许访问 MCP 服务的 IPv4/IPv6 CIDR。为空表示拒绝所有基于 IP 的 MCP 访问。
- **MCP API 令牌**：允许通过 Bearer Token 访问 MCP 服务。

## `config.json` 配置选项

配置节：`security`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `login_whitelist` | 登录 IP 白名单 | 字符串数组 | 登录 IP 白名单 | `[]` |
| `login_tokens` | 登录 API 令牌 | 字符串数组 | 登录 API 令牌 | `[]` |
| `mcp_whitelist` | MCP IP 白名单 | 字符串数组 | MCP IP 白名单 | 局域网与本机 CIDR 或 `[]` |
| `mcp_tokens` | MCP API 令牌 | 字符串数组 | MCP API 令牌 | `[]` |
| `webauthn_rp_id` | Passkey RP ID | 字符串 | 暂无 WebUI 项 | `""` |
| `webauthn_origin` | Passkey Origin | 字符串 | 暂无 WebUI 项 | `""` |

::: warning
令牌请使用足够长的随机字符串，并妥善保管。不要把真实令牌提交到公开仓库。
:::

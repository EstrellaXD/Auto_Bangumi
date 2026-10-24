# 安全设置

![security](/image/config/security.png){width=700}{class=ab-shadow-card}

安全设置用于限制登录入口和 MCP 服务访问。修改后需要点击底部 **保存并重启**。

- **登录 IP 白名单**：允许访问登录接口的 IPv4/IPv6 CIDR。为空表示允许所有 IP。
- **MCP IP 白名单**：允许访问 MCP 服务的 IPv4/IPv6 CIDR。为空表示拒绝所有基于 IP 的 MCP 访问。

API 令牌与 MCP 令牌不在本节。请在 **设置 → 用户与访问控制 → API 令牌** 中创建与撤销，见 [REST API](/api/)。

## `config.json` 配置选项

配置节：`security`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `login_whitelist` | 登录 IP 白名单 | 字符串数组 | 登录 IP 白名单 | `[]` |
| `login_tokens` | 旧版登录 API 令牌，见下方说明 | 字符串数组 | 无 | `[]` |
| `mcp_whitelist` | MCP IP 白名单 | 字符串数组 | MCP IP 白名单 | `[]` |
| `mcp_tokens` | 旧版 MCP API 令牌，见下方说明 | 字符串数组 | 无 | `[]` |
| `webauthn_rp_id` | Passkey RP ID | 字符串 | 暂无 WebUI 项 | `""` |
| `webauthn_origin` | Passkey Origin | 字符串 | 暂无 WebUI 项 | `""` |

::: info
`login_tokens` 与 `mcp_tokens` 是 3.x 的旧配置项。AB 启动时把其中的令牌导入为 API 令牌（作用域分别为 `api` 与 `mcp`），然后清空这两项。
:::

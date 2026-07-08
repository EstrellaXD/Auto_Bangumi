# Security Settings

![security](/image/config/security.png){width=700}{class=ab-shadow-card}

Security settings restrict login and MCP access. Click **Save & restart** after changing them.

- **Login IP Whitelist**: IPv4/IPv6 CIDR ranges allowed to access login. Empty means all IPs are allowed.
- **Login API Tokens**: bearer tokens that can access protected APIs.
- **MCP IP Whitelist**: CIDR ranges allowed to access MCP. Empty means deny IP-based MCP access.
- **MCP API Tokens**: bearer tokens for MCP.

## `config.json`

Section: `security`

| Key | Description | Type | WebUI field | Default |
| --- | --- | --- | --- | --- |
| `login_whitelist` | Login IP whitelist | string array | Login IP Whitelist | `[]` |
| `login_tokens` | Login API tokens | string array | Login API Tokens | `[]` |
| `mcp_whitelist` | MCP IP whitelist | string array | MCP IP Whitelist | local-network CIDRs or `[]` |
| `mcp_tokens` | MCP API tokens | string array | MCP API Tokens | `[]` |
| `webauthn_rp_id` | Passkey RP ID | string | config only | `""` |
| `webauthn_origin` | Passkey origin | string | config only | `""` |

::: warning
Use long random tokens and never commit real tokens to a public repository.
:::

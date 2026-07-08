# セキュリティ設定

![security](/image/config/security.png){width=700}{class=ab-shadow-card}

セキュリティ設定ではログイン入口とMCPアクセスを制限できます。変更後は **保存して再起動** をクリックしてください。

- **ログインIPホワイトリスト**：ログインを許可するIPv4/IPv6 CIDR。空の場合はすべて許可します。
- **ログインAPIトークン**：`Authorization: Bearer <token>` で保護APIへアクセスするためのトークン。
- **MCP IPホワイトリスト**：MCPアクセスを許可するCIDR。空の場合、IPベースのMCPアクセスを拒否します。
- **MCP APIトークン**：MCP用Bearer Token。

## `config.json`

セクション：`security`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `login_whitelist` | ログインIPホワイトリスト | 文字列配列 | ログインIPホワイトリスト | `[]` |
| `login_tokens` | ログインAPIトークン | 文字列配列 | ログインAPIトークン | `[]` |
| `mcp_whitelist` | MCP IPホワイトリスト | 文字列配列 | MCP IPホワイトリスト | ローカルネットワークCIDRまたは `[]` |
| `mcp_tokens` | MCP APIトークン | 文字列配列 | MCP APIトークン | `[]` |
| `webauthn_rp_id` | Passkey RP ID | 文字列 | 設定ファイルのみ | `""` |
| `webauthn_origin` | Passkey Origin | 文字列 | 設定ファイルのみ | `""` |

::: warning
トークンには十分長いランダム文字列を使い、公開リポジトリへコミットしないでください。
:::

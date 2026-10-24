# セキュリティ設定

![security](/image/en/config/security.png){width=700}{class=ab-shadow-card}

セキュリティ設定ではログイン入口とMCPアクセスを制限できます。変更後は **保存して再起動** をクリックしてください。

- **ログインIPホワイトリスト**：ログインを許可するIPv4/IPv6 CIDR。空の場合はすべて許可します。
- **MCP IPホワイトリスト**：MCPアクセスを許可するCIDR。空の場合、IPベースのMCPアクセスを拒否します。

APIトークンとMCPトークンはこのセクションにはありません。**設定 → Users & Access → API Tokens** で作成と取り消しを行います。[REST API](/ja/api/) を参照してください。

## `config.json`

セクション：`security`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `login_whitelist` | ログインIPホワイトリスト | 文字列配列 | ログインIPホワイトリスト | `[]` |
| `login_tokens` | 旧版のログインAPIトークン（下の注を参照） | 文字列配列 | なし | `[]` |
| `mcp_whitelist` | MCP IPホワイトリスト | 文字列配列 | MCP IPホワイトリスト | `[]` |
| `mcp_tokens` | 旧版のMCP APIトークン（下の注を参照） | 文字列配列 | なし | `[]` |
| `webauthn_rp_id` | Passkey RP ID | 文字列 | 設定ファイルのみ | `""` |
| `webauthn_origin` | Passkey Origin | 文字列 | 設定ファイルのみ | `""` |

::: info
`login_tokens` と `mcp_tokens` は 3.x の旧設定項目です。AB は起動時にこれらのトークンを APIトークン（スコープ `api` と `mcp`）として取り込み、両方の項目を空にします。
:::

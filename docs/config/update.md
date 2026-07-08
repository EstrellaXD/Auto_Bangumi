# 软件更新

![update](/image/config/update.png){width=700}{class=ab-shadow-card}

软件更新面板用于检查、应用和回滚 AutoBangumi 更新。

- **更新渠道**：
  - 稳定版：只检查正式 release。
  - 测试版：包含 beta / prerelease。
- **自动检查**：进入设置页时自动检查一次；后端也会周期性检查并写入通知中心。
- **检查更新**：手动刷新当前渠道的最新版本信息。
- **立即更新**：下载、验签、解包并应用更新，然后重启。
- **回滚**：有可回滚版本时显示，回退到上一个已应用版本。

::: warning
应用内更新要求容器以 `restart: unless-stopped` 等策略运行，以便更新后自动重启。更新包会进行 sha256 与 ed25519 签名校验。
:::

## `config.json` 配置选项

配置节：`update`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `channel` | 更新渠道，`stable` 或 `beta` | 字符串 | 更新渠道 | `stable` |
| `auto_check` | 自动检查更新 | 布尔值 | 自动检查 | `true` |

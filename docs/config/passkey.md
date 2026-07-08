# Passkey 设置

![passkey](/image/config/passkey.png){width=700}{class=ab-shadow-card}

Passkey 设置用于管理当前账户可用的 WebAuthn / Passkey 登录凭据。

- **添加 Passkey**：输入设备名称后，按浏览器或系统提示完成验证。
- **删除**：移除不再使用的设备凭据。
- **最后使用**：已使用过的 Passkey 会显示最后使用时间。
- **已同步到多设备**：表示该 Passkey 支持跨设备同步。

::: tip
Passkey 列表是即时保存项，不需要点击底部 **保存并重启**。浏览器必须支持 WebAuthn，且反向代理部署时应正确配置 HTTPS 与域名。
:::

## 相关安全配置

高级部署可以在 `security` 配置节中设置：

| 参数 | 说明 |
| --- | --- |
| `webauthn_rp_id` | WebAuthn Relying Party ID。留空时根据请求头推断 |
| `webauthn_origin` | 期望的 WebAuthn Origin。留空时根据请求头推断 |

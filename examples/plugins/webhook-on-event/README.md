# 事件 Webhook（示例插件）

把选中的事件以 JSON POST 到一个 URL。演示：

- `@subscribe("*")` 订阅全部事件，按配置过滤
- `config_model`（WebUI 自动生成表单）与 `secret_field`（密码框、读取时掩码）
- 用 `ab_sdk.testing.create_plugin` 在不启动 AutoBangumi 的情况下测试

## 安装

```bash
cp -r examples/plugins/webhook-on-event config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写地址。

## 测试

```bash
cd examples/plugins/webhook-on-event && uv run pytest
```

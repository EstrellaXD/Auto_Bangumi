# ntfy 通知（示例插件）

把通知发到 [ntfy](https://ntfy.sh) 主题。演示：

- `@provider(points.NOTIFIER, id="ntfy")`：返回 `NotifierFactory`
- 凭据放在插件的 `config_model` 里，渠道条目只带通用模板
- 后端拒绝时 `send` 返回 `False` 而不抛异常
- 契约套件 `NotifierContract`

## 安装

```bash
cp -r examples/plugins/ntfy-notifier config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写主题；再到「设置 → 通知 → 添加渠道」选择类型 `ntfy`。

## 测试

```bash
cd examples/plugins/ntfy-notifier && uv run pytest
```

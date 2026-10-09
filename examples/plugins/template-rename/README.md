# 过滤器模板重命名（示例插件）

自带过滤器的文件名模板，如 `{bangumi_name|sanitize} S{season|pad:2}E{episode|pad:2}`。演示：

- `@provider(points.RENAME_STRATEGY)`：返回 `RenameStrategy`
- 渲染不出可用文件名时抛 `RenameSkipped`：宿主保留原文件名并通知，不计入熔断
- 在 `field_validator` 里提前校验模板，写错的模板保存时就被拒绝
- 契约套件 `RenameStrategyContract`

## 安装

```bash
cp -r examples/plugins/template-rename config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」并启用，再到「番剧管理设置 → 重命名方式」选择 `mini-template`。

## 测试

```bash
cd examples/plugins/template-rename && uv run pytest
```

# WPUSH 通知

把通知发到 [WPUSH](https://wpush.cn)，支持微信、短信、邮件等渠道。

- `@provider(points.NOTIFIER, id="wpush")`：返回 `NotifierFactory`
- 向 `https://api.wpush.cn/api/v1/send` POST JSON：`apikey`、`title`、`content`、`channel`，填写了群组编码时附带 `topic_code`
- HTTP 2xx 且返回的 `code` 为 0 才算成功；否则 `send` 返回 `False`，「测试」显示 WPUSH 返回的错误信息

## 配置

| 字段 | 说明 |
| --- | --- |
| `apikey` | WPUSH 控制台中的 apikey（秘密字段） |
| `channel` | 推送渠道，默认 `wechat` |
| `topic_code` | 可选：群组编码 |

## 安装

```bash
cp -r examples/plugins/wpush-notifier config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写 apikey；再到「设置 → 通知 → 添加渠道」选择类型 `wpush`。

## 测试

```bash
cd examples/plugins/wpush-notifier && uv run pytest
```

---

基于 @anhao 在 [#1116](https://github.com/EstrellaXD/Auto_Bangumi/pull/1116) 中的实现

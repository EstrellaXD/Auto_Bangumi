# 解析器设置

AB 的解析器用于分析 RSS 条目标题，并生成番剧、季度、集数、字幕组等结构化信息。

::: tip
从 v3.1 开始，单个 RSS 的解析器类型在添加或编辑 RSS 时设置。这里的 **解析设置** 是全局开关、语言与过滤规则。
:::

## WebUI 配置

![parser](/image/config/parser.png){width=700}{class=ab-shadow-card}

- **启用**：是否启用 RSS 解析器。关闭后不会自动解析新 RSS 条目。
- **语言**：解析器偏好的标题语言，目前支持 `zh`、`jp` 和 `en`。
- **排除**：全局过滤规则。可以输入普通字符串或正则表达式，匹配到的 RSS 条目会在解析阶段被过滤。

## `config.json` 配置选项

配置节：`rss_parser`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `enable` | 启用 RSS 解析器 | 布尔值 | 启用 | `true` |
| `filter` | 全局过滤规则 | 字符串数组 | 排除 | `["720", "\\d+-\\d+"]` |
| `language` | 解析语言 | 字符串 | 语言 | `zh` |

[add_rss]: /feature/rss#parser-settings

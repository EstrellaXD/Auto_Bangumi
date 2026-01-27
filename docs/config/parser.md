# 解析器设置

AB 的解析器用于解析聚合 RSS 链接。当 RSS 订阅中出现新条目时，AB 会解析标题并生成自动下载规则。

::: tip
从 v3.1 开始，解析器设置已移至各个 RSS 的单独设置中。要配置**解析器类型**，请参阅 [RSS 解析器设置][add_rss]。
:::

## WebUI 中的解析器设置

![parser](../image/config/parser.png){width=500}{class=ab-shadow-card}

<br/>

- **启用**：是否启用 RSS 解析器。
- **语言** 为 RSS 解析器语言。目前支持 `zh`、`jp` 和 `en`。
- **过滤** 为全局 RSS 解析器过滤规则。可以输入字符串或正则表达式，AB 会在 RSS 解析时过滤掉匹配的条目。

## `config.json` 配置选项

配置文件中的对应选项如下：

配置节：`rss_parser`

| 参数     | 说明             | 类型    | WebUI 选项        | 默认值         |
|----------|------------------|---------|-------------------|----------------|
| enable   | 启用 RSS 解析器  | 布尔值  | 启用 RSS 解析器   | true           |
| filter   | RSS 解析器过滤   | 数组    | 过滤              | [720,\d+-\d+] |
| language | RSS 解析器语言   | 字符串  | RSS 解析器语言    | zh             |


[rss_token]: rss
[add_rss]: /feature/rss#parser-settings
[reproxy]: proxy#reverse-proxy

# 解析器设置

AB 的解析器用于解析聚合 RSS 链接，如果 RSS 有新条目更新，AB 就会解析标题并且生成自动下载规则。

::: tip
v3.1 版本以后解析器设置迁移到各个单独的 RSS 设置中，如果需要配置**解析器类型**，请参考 [为 RSS 设定解析器][add_rss]。
:::

## Webui 中的解析器设置

![parser](../image/config/parser.png){width=500}{class=ab-shadow-card}

<br/>

- **Enable / 启用**: 是否启用 RSS 解析器。
- **Language** 为 RSS 解析器语言，目前支持 `zh` 、 `jp` 、 `en` 三种语言。
- **Exclude** 为全局 RSS 解析器过滤器，可以填入字符串或者正则表达式，AB 在解析 RSS 时会过滤掉符合过滤器的条目。

## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`rss_parser`

| 参数名      | 参数说明        | 参数类型 | WebUI 对应选项  | 默认值           |
|----------|-------------|------|-------------|---------------|
| enable   | RSS 解析器是否启用 | 布尔值  | RSS 解析器是否启用 | true          |
| filter   | RSS 解析器过滤器  | 数组   | 过滤器         | [720,\d+-\d+] |
| language | RSS 解析器语言   | 字符串  | RSS 解析器语言   | zh            |


[rss_token]: rss
[add_rss]: /feature/rss#解析器设置
[reproxy]: proxy##反向代理设置
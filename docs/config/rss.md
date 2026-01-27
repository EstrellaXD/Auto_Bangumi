# RSS 订阅设置

AutoBangumi 可以自动解析聚合 RSS 订阅源，并根据字幕组和番剧名称生成下载规则，实现全自动追番。
以下以 [Mikan Project][mikan-site] 为例，说明如何获取 RSS 订阅链接。

请注意，Mikan Project 主站在部分地区可能被屏蔽。如果无法直接访问，请使用以下备用域名：

[Mikan Project (备用)][mikan-cn-site]

## 获取订阅链接

本项目基于 Mikan Project 提供的 RSS 链接进行解析。要启用自动追番功能，您需要注册并获取 Mikan Project 的 RSS 链接：

![image](/image/rss/rss-token.png){data-zoomable}

RSS 链接格式如下：

```txt
https://mikanani.me/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# 或
https://mikanime.tv/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Mikan Project 订阅注意事项

由于 AutoBangumi 会解析接收到的所有 RSS 条目，订阅时请注意以下几点：

![image](/image/rss/advanced-subscription.png){data-zoomable}

- 在个人设置中启用高级选项。
- 每部番剧只订阅一个字幕组。点击 Mikan Project 上的番剧海报打开子菜单，选择单个字幕组。
- 如果字幕组同时提供简体和繁体中文字幕，Mikan Project 通常会提供选择方式，请选择其中一种。
- 如果没有字幕类型选择选项，可以在 AutoBangumi 中设置 `filter` 进行过滤，或在规则生成后在 qBittorrent 中手动过滤。
- 目前不支持解析 OVA 和剧场版订阅。


[mikan-site]: https://mikanani.me/
[mikan-cn-site]: https://mikanime.tv/

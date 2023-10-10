# 搜索功能

在 3.1 版本之后 AB 添加了搜索功能，可以通过搜索功能快速找到想要的番剧。

## 使用搜索功能

::: warning
搜索功能依赖主程序的解析器，当前版本不允许解析合集。解析合集提示 `warning` 为正常现象。
:::

搜索栏位于 AB 顶栏，可以在搜索栏右侧选择想要搜索的源站，比如：蜜柑计划、nyaa 等

选择对应的源站输入关键词，AB 即可自动解析搜索结果并展示。如果想要添加对应的番剧，点击卡片右侧的添加按钮即可。

::: tip
源站为 **Mikan** 是 AB 默认使用 `mikan` 解析器，如果使用其他源站，默认使用 TMDB 解析器。
:::

## 增加源站

用户可以手动增加源站列表，只需要更改 `config/search_provider.json` 即可。
默认为
```json
{
  "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
  "nyaa": "https://nyaa.si/?page=rss&q=%s&c=0_0&f=0",
  "dmhy": "http://dmhy.org/topics/rss/rss.xml?keyword=%s",
  "bangumi.moe": "https://bangumi.moe/rss/search/%s"
}
```
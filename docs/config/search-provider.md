# 搜索源设置

![search provider](/image/config/search-provider.png){width=700}{class=ab-shadow-card}

搜索源用于 WebUI 的种子搜索与订阅。内置源包括 `mikan`、`nyaa` 和 `dmhy`；默认源不能删除，但可以编辑 URL 模板。

搜索源设置是即时保存项，添加、编辑或删除后会立即写入 `config/search_provider.json`，不需要点击底部 **保存并重启**。

## 添加自定义搜索源

自定义 URL 模板必须包含 `%s`，AB 会把搜索关键词替换到这个位置。

```txt
https://example.com/search?q=%s
```

## PT 站点（NexusPHP）

![NexusPHP search provider](/image/config/search-provider-nexusphp.png){width=700}{class=ab-shadow-card}

PT 站点模式会根据站点地址、Passkey 和可选分类 ID 生成 `torrentrss.php` RSS 搜索模板。

::: warning
部分新版原生 NexusPHP 已停用 `search` 参数，可能对任意关键词都返回最新种子。添加前请先在站点上确认 RSS 搜索会按关键词过滤。
:::

## `search_provider.json` 配置选项

默认文件路径：`config/search_provider.json`

```json
{
  "mikan": {
    "url": "https://mikanani.me/RSS/Search?searchstr=%s",
    "parser": "mikan"
  },
  "nyaa": {
    "url": "https://nyaa.si/?page=rss&q=%s&c=0_0&f=0",
    "parser": "tmdb"
  }
}
```

| 参数 | 说明 |
| --- | --- |
| `url` | 搜索 URL 模板，必须包含 `%s` |
| `parser` | 搜索结果使用的解析器。旧格式只有 URL 字符串时会自动补默认解析器 |

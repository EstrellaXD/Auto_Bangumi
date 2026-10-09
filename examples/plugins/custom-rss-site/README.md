# 自定义 RSS 站点（示例插件）

给搜索框加一个站点，并为该站点的请求附带 Cookie。演示：

- `@provider(points.SEARCH_SITE)`：返回 `SearchSite`
- `@hook(points.HTTP_REQUEST)`：transform 钩子，返回修改后的请求副本；返回 `None` 表示不修改
- 契约套件 `SearchSiteContract`

## 安装

```bash
cp -r examples/plugins/custom-rss-site config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写搜索地址与 Cookie。

## 测试

```bash
cd examples/plugins/custom-rss-site && uv run pytest
```

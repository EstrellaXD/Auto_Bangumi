# 网络设置

![network](/image/config/network.png){width=700}{class=ab-shadow-card}

网络设置用于覆盖外部元数据服务地址和凭据。修改后需要点击底部 **保存并重启**。

- **TMDB API 地址**：默认 `https://api.themoviedb.org`。网络受限时可改为可访问的反代地址。
- **TMDB API Key（可选）**：留空时使用内置共享 key；自配 key 可以避开共享 key 的限流。
- **Bangumi API 地址**：默认 `https://api.bgm.tv`。

## `config.json` 配置选项

配置节：`network`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `tmdb_base_url` | TMDB API 地址 | 字符串 | TMDB API 地址 | `https://api.themoviedb.org` |
| `tmdb_api_key` | 自定义 TMDB API Key | 字符串 | TMDB API Key（可选） | `""` |
| `bgm_base_url` | Bangumi API 地址 | 字符串 | Bangumi API 地址 | `https://api.bgm.tv` |

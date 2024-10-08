# 番剧管理设置

## WebUI 配置

![proxy](../image/config/manager.png){width=500}{class=ab-shadow-card}

<br/>

- **Enable** 为是否启用番剧管理，如果不启用番剧管理，下面的配置项将不会生效。
- **Rename method** 为重命名方式，目前支持
  - `pn` 为 `Torrent Title S0XE0X.mp4` 的方式。
  - `advance` 为 `Official Title S0XE0X.mp4` 的方式。
  - `none` 为不重命名。
- **Eps complete** 为是否补全当季番剧，如果开启，则会补全当季番剧，如果关闭，则不会补全当季番剧。
- **Add group tag** 为是否在下载规则中添加番剧组标签，如果开启，则会在下载规则中添加番剧组标签。
- **Delete bad torrent** 为是否删除错误的种子，如果开启，则会删除错误的种子。
- **Customize Save Path Pattern** 为自定义保存路径格式，支持模板字符串，会在生成保存路径时自动替换模板变量。
- [关于文件路径][1]
- [关于重命名][2]

## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`bangumi_manager`

| 参数名                | 参数说明            | 参数类型 | WebUI 对应选项 | 默认值  |
|--------------------|-----------------|------|------------|------|
| enable             | 番剧管理是否启用        | 布尔值  | 番剧管理是否启用   | true |
| eps_complete       | 是否补全当季番剧        | 布尔值  | 番剧补全       | false |
| rename_method      | 重命名方式           | 字符串  | 重命名方式      | pn   |
| group_tag          | 是否在下载规则中添加番剧组标签 | 布尔值  | 番剧组标签      | false |
| remove_bad_torrent | 是否删除错误的种子       | 布尔值  | 种子删除       | false |
| customize_path_pattern | 自定义保存路径格式       | 字符串  | 自定义保存路径格式       | ''  |

## 自定义保存路径说明

当前支持的模板变量:

- **official_title**: 番剧中文名
- **year**: 番剧年份（可能为空）
- **title_raw**: 番剧原名
- **season**: 番剧季度
- **season_raw**: 番剧季度原名（可能为空）
- **group_name**: 字幕组（可能为空）
- **download_path**: 在下载设置中配置的【下载地址】

自定义保存路径格式示例: `/${download_path}/${year}/${official_title}`

注意，部分字段为空时会跳过解析，例如上边示例中当 year 为空时，最终用来解析的路径是 `/${download_path}/${official_title}`。

[1]:   https://www.autobangumi.org/faq/#%E4%B8%8B%E8%BD%BD%E4%BB%A5%E5%8F%8A%E5%85%B3%E9%94%AE%E8%AF%8D%E8%BF%87%E6%BB%A4
[2]:   https://www.autobangumi.org/faq/#%F0%9F%93%81-%E9%87%8D%E5%91%BD%E5%90%8D%E7%9B%B8%E5%85%B3

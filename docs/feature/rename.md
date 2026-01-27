# 文件重命名

AB 目前提供三种重命名方式：`pn`、`advance` 和 `none`。

### pn

`pure name` 的缩写。此方法使用种子下载名称进行重命名。

示例：
```
[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six S01E01.mkv
```

### advance

高级重命名。此方法使用父文件夹名称进行重命名。

```
/downloads/Bangumi/86 - Eighty Six(2023)/Season 1/[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six(2023) S01E01.mkv
```

### none

不重命名。文件保持原样。

## 收藏重命名

AB 支持收藏重命名。收藏重命名需要：
- 剧集位于收藏的一级目录中
- 可以从文件名解析出剧集编号

AB 还可以重命名一级目录中的字幕文件。

重命名后，剧集和目录将放置在 `Season` 文件夹中。

重命名后的收藏将被移动并归类到 `BangumiCollection` 下。

## 剧集偏移

从 v3.2 开始，AB 支持重命名时的剧集偏移。在以下情况下很有用：
- RSS 显示的剧集编号与预期不同（例如 S2E01 应该是 S1E29）
- 番剧因播出间隔而产生"虚拟季度"

当为番剧配置偏移后，AB 会在重命名时自动应用：

```
原始：S02E01.mkv
应用偏移（季度：-1，剧集：+28）：S01E29.mkv
```

配置偏移：
1. 点击番剧海报
2. 打开高级设置
3. 设置季度偏移和/或剧集偏移值
4. 或使用"自动检测"让 AB 建议正确的偏移

有关自动检测的更多详情，请参阅[番剧管理](./bangumi.md#episode-offset-auto-detection)。

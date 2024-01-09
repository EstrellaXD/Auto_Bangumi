# 重命名使用说明

AB 现在提供了三种重命名方式，分别为 `pn`、`advance` 和 `none`。

### pn

全称为 `pure name`，即纯番剧名，这种方式会把番剧名作为文件名，不会添加任何前缀。

pn 根据种子文件的下载名称进行重命名。
如：
```
[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six S01E01.mkv
```

### advance

高级重命名，这种方式会把文件夹名用于重命名。

```
/downloads/Bangumi/86 - Eighty Six(2023)/Season 1/[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six(2023) S01E01.mkv
```

### none

不重命名，这种方式不会对文件进行重命名。

## 合集重命名

AB 支持对合集进行重命名，合集重命名需要满足以下条件：
- 剧集都在合集的一级目录下
- 可以解析出剧集的集数

同时 AB 也可以对在一级目录下的字幕文件进行重命名。

重命名之后的剧集和目录都会被放到 `Season` 文件夹下。

重命名的合集会被移动分类至 `BangumiCollection`。
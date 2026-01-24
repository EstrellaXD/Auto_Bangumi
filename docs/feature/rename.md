# File Renaming

AB currently provides three renaming methods: `pn`, `advance`, and `none`.

### pn

Short for `pure name`. This method uses the torrent download name for renaming.

Example:
```
[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six S01E01.mkv
```

### advance

Advanced renaming. This method uses the parent folder name for renaming.

```
/downloads/Bangumi/86 - Eighty Six(2023)/Season 1/[Lilith-Raws] 86 - Eighty Six - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MKV].mkv
>>
86 - Eighty Six(2023) S01E01.mkv
```

### none

No renaming. Files are left as-is.

## Collection Renaming

AB supports renaming collections. Collection renaming requires:
- Episodes are in the collection's first-level directory
- Episode numbers can be parsed from file names

AB can also rename subtitle files in the first-level directory.

After renaming, episodes and directories are placed in the `Season` folder.

Renamed collections are moved and categorized under `BangumiCollection`.

# 番剧管理设置

## WebUI 配置

![manager](/image/config/manager.png){width=700}{class=ab-shadow-card}

- **启用**：启用番剧管理器。关闭后，重命名与整理相关设置不会生效。
- **重命名方式**：
  - `normal`：使用较保守的番剧标题与集数命名。
  - `pn`：保留更多发布标题信息，使用 `种子标题 S0XE0X` 风格。
  - `advance`：使用官方标题与标准季集格式。
  - `none`：不重命名文件。
- **番剧补全**：检测当季缺失集数并尝试补全下载。
- **添加组标签**：为下载器中的任务添加字幕组相关标签。
- **删除坏种**：移除下载器中状态异常的种子。
- **记录未匹配种子**：把当前没有匹配到规则的种子记录为“未匹配种子”。关闭后，后续新增规则可以立即接住 RSS 中仍存在的旧条目，但这些旧条目会在每轮 RSS 刷新时重新尝试匹配。
- [关于文件路径][1]
- [关于重命名][2]

## `config.json` 配置选项

配置节：`bangumi_manage`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `enable` | 启用番剧管理器 | 布尔值 | 启用 | `true` |
| `eps_complete` | 启用剧集补全 | 布尔值 | 番剧补全 | `false` |
| `rename_method` | 重命名方式 | 字符串 | 重命名方式 | `pn` |
| `group_tag` | 添加字幕组标签 | 布尔值 | 添加组标签 | `false` |
| `remove_bad_torrent` | 删除错误种子 | 布尔值 | 删除坏种 | `false` |
| `track_orphans` | 记录未匹配种子 | 布尔值 | 记录未匹配种子 | `true` |

[1]: https://www.autobangumi.org/faq/#download-path
[2]: https://www.autobangumi.org/faq/#file-renaming

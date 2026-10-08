# 番剧管理设置

## WebUI 配置

![manager](/image/config/manager.png){width=700}{class=ab-shadow-card}

- **启用**：启用番剧管理器。关闭后，重命名与整理相关设置不会生效。
- **重命名方式**：
  - `pn`：保留更多发布标题信息，使用 `种子标题 S0XE0X` 风格。
  - `advance`：使用官方标题与标准季集格式。
  - `none`：不重命名文件。
  - `template`：按自定义模板命名，见下文[模板重命名](#模板重命名)。
  - 插件也可以提供更多重命名方式，启用后会出现在下拉框中。
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

## 模板重命名

选择 `template` 后，文件名由内置插件「模板重命名」（`rename-template`）生成。在 **设置 → 插件 → 模板重命名** 中修改模板：

| 选项 | 说明 | 默认值 |
| --- | --- | --- |
| 剧集模板 | 普通剧集使用的模板 | `{{ title }} S{{ season\|pad(2) }}E{{ episode\|pad(2) }}` |
| 剧场版模板 | 剧场版使用的模板 | `{{ title }}` |

默认模板与 `pn` 的结果完全相同。模板使用 [Jinja2](https://jinja.palletsprojects.com/) 语法（沙箱模式），可用变量：

| 变量 | 含义 | 示例 |
| --- | --- | --- |
| `title` | 从文件名解析出的标题 | `葬送的芙莉莲` |
| `bangumi_name` | 番剧文件夹名 | `葬送的芙莉莲 (2023)` |
| `season` | 季度（已含季度偏移） | `1` |
| `episode` | 集数（已含剧集偏移，半集保留小数） | `5`、`12.5` |
| `group` | 字幕组，可能为空 | `ANi` |
| `episode_type` | `episode` / `movie` / `special` | `episode` |
| `kind` | `media` 或 `subtitle` | `media` |
| `language` | 字幕语言，媒体文件为空 | `zh` |

`pad(n)` 过滤器把数字补零到 n 位，如 `{{ episode|pad(3) }}` 得到 `005`。

- 模板只生成文件名主体，扩展名会自动追加；字幕文件追加 `.语言.扩展名`，如 `.zh.ass`。
- 渲染结果为空、含 `/` 或 `\`、或使用了不存在的变量时，该文件保持原名，并在日志中记录错误。
- 保存语法错误的模板会被直接拒绝。

示例：`[{{ group }}] {{ bangumi_name }} - {{ episode|pad(2) }}` → `[ANi] 葬送的芙莉莲 (2023) - 05.mkv`

::: warning
更换重命名方式（包括修改模板）后，新完成的下载会使用新的命名；已整理完成的种子不会被重新命名。
:::

[1]: https://www.autobangumi.org/faq/#download-path
[2]: https://www.autobangumi.org/faq/#file-renaming

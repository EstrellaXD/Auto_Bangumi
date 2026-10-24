# 重命名方式（rename_strategy）

下载完成后，AB 为种子里的每个正片与字幕调用「重命名方式」（`plugins.slots.rename_strategy`）对应的 Provider。宿主只自带 `none`（保留原名）；`pn`、`advance`、`template` 由内置插件 `rename` 提供。插件登记的 `id` 出现在 设置 → 番剧管理设置 → 重命名方式 的下拉框里。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.rename import RenameInput, RenameSkipped, pad


class JellyfinStyle:
    def target_name(self, f: RenameInput) -> str:
        language = f".{f.language}" if f.kind == "subtitle" else ""
        if f.episode_type == "movie":
            return f"{f.bangumi_name}{language}{f.suffix}"
        if not f.bangumi_name:
            raise RenameSkipped("缺少番剧文件夹名")
        return f"{f.bangumi_name} - S{pad(f.season)}E{pad(f.episode)}{language}{f.suffix}"


class MyRename(Plugin):
    @provider(points.RENAME_STRATEGY, id="jellyfin-style")
    def jellyfin(self):
        return JellyfinStyle()
```

## RenameInput

冻结快照。

| 字段 | 说明 |
| --- | --- |
| `kind` | `media` 或 `subtitle`（字幕没有单独的方式，按 `kind` 区分） |
| `media_path` | 种子内的原相对路径 |
| `title` | 解析自文件名的标题 |
| `bangumi_name` | 保存目录的番剧文件夹名（电影为 `Title (Year)`） |
| `season`、`episode` | 季与集；`episode` 已应用集数偏移 |
| `suffix` | 含点的扩展名，如 `.mkv` |
| `episode_type` | `episode`、`movie` 或 `special` |
| `language` | 字幕语言，如 `zh`、`zh-tw` |
| `group` | 字幕组，可能为 `None` |

`title` 和 `bangumi_name` 来自磁盘上已有的文件名或文件夹名，是单个路径分量，AB 不做保留字符清洗。

## 返回值与错误

- 返回种子内的新相对路径，通常只是文件名。扩展名和字幕语言由策略自己拼上。返回 `f.media_path` 表示不改名。
- `pad(n, width=2)` 补零并保留半集的小数：`pad(9.5) == "09.5"`。总集篇等半集必须保留小数，否则会覆盖同季的整数集。
- 抛出 `RenameSkipped(原因)`：该文件保留原名，种子不打「已重命名」标签，每个种子按原因发一条 `rename_skipped` 通知。修正后下一轮自动重试。它表示输入或配置有问题，不计入熔断。**不要在失败时退回别的命名方式。**
- 抛出其它异常、返回空串或非字符串：同样保留原名并通知，同时计入熔断。
- `target_name` 是同步调用，没有超时，不要在里面做网络或磁盘 IO。
- 设置里选择的 `id` 没有登记（插件被停用或熔断）时，AB 记录一次日志并按 `none` 处理。

## 测试

```python
from ab_sdk.testing import RenameStrategyContract, create_plugin

class TestStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin(MyRename)
        return plugin.jellyfin()
```

套件检查：返回非空的相对路径、不含 `..`、保留扩展名、结果确定。适用于特定输入时，覆盖 `samples()`。

示例：`examples/plugins/template-rename`（自带过滤器的模板）。

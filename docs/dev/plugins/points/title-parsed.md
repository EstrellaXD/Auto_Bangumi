# 修正解析结果（title.parsed）

transform 钩子。在确定性解析（以及启用时的 LLM 解析）之后、准入判定之前调用。收到冻结的解析结果，用 `dataclasses.replace` 返回修改后的副本；返回 `None` 表示不修改。返回其它类型会被忽略并计入熔断。

```python
from dataclasses import replace

from ab_sdk import Plugin, hook, points

ALIASES = {"LoliHouse": "Lolihouse"}


class GroupAlias(Plugin):
    @hook(points.TITLE_PARSED)
    def fix(self, release):
        if release.group in ALIASES:
            return replace(release, group=ALIASES[release.group])
        return None
```

- 可读字段：`raw`、`title_en`、`title_zh`、`title_jp`、`group`、`season`、`episode`、`resolution`、`source`、`subtitle`、`year`。这些之外的属性（`media_type`、`release_kind` 等）可读，但 SDK 1.0 之前不保证稳定。
- 新规则的番剧名、季度、字幕组都来自这里的结果，所以修改会影响新建的规则。
- 改成 PV、合集等类型会让该资源不被收录。

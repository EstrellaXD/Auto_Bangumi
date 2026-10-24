# 解析結果の補正 (title.parsed)

transform フックです。AB は、決定的な解析の後（LLM 解析が有効ならその後）、受け入れ判定の前にこれを呼びます。フックは凍結された解析結果を受け取ります。`dataclasses.replace` で作った変更後のコピーを返します。`None` は変更なしです。他の型の戻り値は無視され、ブレーカーに数えられます。

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

- 読めるフィールド：`raw`、`title_en`、`title_zh`、`title_jp`、`group`、`season`、`episode`、`resolution`、`source`、`subtitle`、`year`。これ以外の属性（`media_type`、`release_kind` など）も読めますが、SDK 1.0 までは安定性が保証されません。
- 新しいルールの作品名、シーズン、字幕グループは、この結果に由来します。そのため、ここでの変更は新しく作られるルールに影響します。
- 種別を PV や合集などに変えると、AB はそのリソースを取り込みません。

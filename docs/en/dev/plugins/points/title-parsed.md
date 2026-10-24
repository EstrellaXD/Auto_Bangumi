# Parsed Title (title.parsed)

A transform hook. AB calls it after the deterministic parse (and after the LLM parse, if enabled) and before the admission check. The hook receives the frozen parse result. Return a changed copy made with `dataclasses.replace`. `None` means no change. AB ignores a return value of another type, and it counts toward the breaker.

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

- Readable fields: `raw`, `title_en`, `title_zh`, `title_jp`, `group`, `season`, `episode`, `resolution`, `source`, `subtitle`, `year`. You can read other attributes (`media_type`, `release_kind` and more), but they are not stable before SDK 1.0.
- The series name, the season and the release group of a new rule come from this result. A change here therefore affects the rules that AB creates.
- If you change the type to PV, batch release or similar, AB does not accept the resource.

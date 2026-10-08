# Conflict Policy (conflict_policy)

When the canonical file name of a new torrent is already used by another torrent, this policy decides to keep the old one or to replace it. A typical case is a v2 release of the same episode. `@provider(points.CONFLICT_POLICY, id=...)` returns a `ConflictPolicy`.

```python
from ab_sdk.rename import ConflictDecision, ConflictRequest

class ReplaceUpgradesOnly:
    def decide(self, request: ConflictRequest) -> ConflictDecision:
        if request.strict_upgrade:
            return ConflictDecision("replace")
        return ConflictDecision("hold", "not a higher version of the same release")
```

- `ConflictRequest`: `target_path`, `incoming` (the new torrent), `owners` (the torrents that use the name), `strict_upgrade` (the only owner is the same release as the new torrent and the new torrent has a higher version number).
- `hold` keeps the old file and the new torrent waits. AB shows the `reason` to the user. `replace` **deletes the old task and its files**.
- The host executes `replace` only when there is one owner, both torrents have a single file and both have a complete parsed identity. In all other cases AB treats the result as `hold`.
- The host has `hold` and `replace`. They are the two options of the setting "revision conflict policy". `plugins.slots.conflict_policy` selects the policy (default `hold`). If the selected id is not registered, AB uses `hold`.

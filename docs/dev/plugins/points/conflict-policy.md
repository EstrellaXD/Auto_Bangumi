# 版本冲突策略（conflict_policy）

新种子的规范文件名已被另一个种子占用时，决定保留旧的还是替换。典型场景：同一集的 v2 发布。`@provider(points.CONFLICT_POLICY, id=...)` 返回 `ConflictPolicy`。

```python
from ab_sdk.rename import ConflictDecision, ConflictRequest

class ReplaceUpgradesOnly:
    def decide(self, request: ConflictRequest) -> ConflictDecision:
        if request.strict_upgrade:
            return ConflictDecision("replace")
        return ConflictDecision("hold", "不是同一发布的更高版本")
```

- `ConflictRequest`：`target_path`、`incoming`（新种子）、`owners`（占用者）、`strict_upgrade`（唯一占用者与新种子是同一发布，且新种子版本号更高）。
- `hold` 保留旧文件，新种子等待；`reason` 展示给用户。`replace` **删除旧任务及其文件**。
- 宿主只在「唯一占用者、双方都是单文件种子、双方解析身份完整」时执行 `replace`，其它情况一律按 `hold` 处理。
- 宿主自带 `hold` 与 `replace`，即设置项「版本冲突策略」的两个选项。用 `plugins.slots.conflict_policy` 选择（默认 `hold`）。选中的 id 未登记时，退回 `hold`。

# 定时任务（scheduled_task）

增加一个周期执行的后台任务。`@provider(points.SCHEDULED_TASK, id=...)` 返回 `ScheduledTask`。

```python
from ab_sdk.tasks import ScheduledTask

@provider(points.SCHEDULED_TASK, id="sync")
def sync(self):
    async def run() -> None:
        ...

    return ScheduledTask(run, interval=lambda: self.config.interval, initial_delay=60)
```

| 字段 | 说明 |
| --- | --- |
| `run` | 无参数的异步函数 |
| `interval` | 两次执行之间的间隔（秒）。可以是函数，每轮重新读取，以便跟随配置变化 |
| `initial_delay` | 首次执行前先等待的秒数，默认 0 |
| `enabled` | 可选的函数，返回 `False` 时本轮跳过 |

- 任务只在程序运行时执行，与 RSS 刷新等内置任务一同启停。
- `run` 抛出的异常计入插件熔断。
- 间隔从上一次执行结束时算起，不是固定节拍。

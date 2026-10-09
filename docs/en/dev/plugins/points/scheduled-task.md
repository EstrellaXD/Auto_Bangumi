# Scheduled Task (scheduled_task)

Adds a periodic background task. `@provider(points.SCHEDULED_TASK, id=...)` returns a `ScheduledTask`.

```python
from ab_sdk.tasks import ScheduledTask

@provider(points.SCHEDULED_TASK, id="sync")
def sync(self):
    async def run() -> None:
        ...

    return ScheduledTask(run, interval=lambda: self.config.interval, initial_delay=60)
```

| Field | Description |
| --- | --- |
| `run` | An async function with no parameters |
| `interval` | The wait between two runs, in seconds. It can be a function. AB reads it again each round, so it follows configuration changes |
| `initial_delay` | The seconds to wait before the first run. Default 0 |
| `enabled` | An optional function. If it returns `False`, AB skips that round |

- The task runs only while the program runs. It starts and stops together with built-in tasks such as the RSS refresh.
- An exception from `run` counts toward the plugin breaker.
- The interval starts when the previous run ends. It is not a fixed beat.

# 定期タスク (scheduled_task)

定期的に実行するバックグラウンドタスクを追加します。`@provider(points.SCHEDULED_TASK, id=...)` は `ScheduledTask` を返します。

```python
from ab_sdk.tasks import ScheduledTask

@provider(points.SCHEDULED_TASK, id="sync")
def sync(self):
    async def run() -> None:
        ...

    return ScheduledTask(run, interval=lambda: self.config.interval, initial_delay=60)
```

| フィールド | 説明 |
| --- | --- |
| `run` | 引数のない async 関数 |
| `interval` | 2 回の実行の間隔（秒）。関数にでき、毎回読み直されるため設定の変更に追従します |
| `initial_delay` | 最初の実行までに待つ秒数。既定は 0 |
| `enabled` | 任意の関数。`False` を返すと、その回はスキップします |

- タスクはプログラムの動作中だけ実行されます。RSS 更新などの組み込みタスクと一緒に起動・停止します。
- `run` が送出した例外は、プラグインのブレーカーに数えられます。
- 間隔は前回の実行が終わった時点から数えます。固定の拍ではありません。

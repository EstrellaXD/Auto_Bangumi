"""定时任务契约。"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduledTask:
    """由宿主调度器周期执行的任务。

    ``run`` 执行一次后等待 ``interval`` 秒再执行下一次；``interval`` 与
    ``enabled`` 可以是可调用对象，每轮都会重新读取，以便跟随插件配置变化。
    ``initial_delay`` 大于 0 时首次执行前先等待。任务只在程序运行时执行
    （与 RSS 刷新等内置任务一同启停），失败会计入插件熔断。
    """

    run: Callable[[], Awaitable[None]]
    interval: float | Callable[[], float]
    initial_delay: float = 0.0
    enabled: Callable[[], bool] | None = None

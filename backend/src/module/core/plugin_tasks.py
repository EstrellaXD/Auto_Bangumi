"""把插件以 points.SCHEDULED_TASK 登记的任务同步进调度器。"""

import logging

from ab_sdk import points
from ab_sdk.tasks import ScheduledTask
from module.plugin.registry import ExtensionRegistry, ProviderEntry
from module.plugin.runner import CircuitBreaker

from .scheduler import PeriodicTask, Scheduler

logger = logging.getLogger(__name__)


class PluginTasks:
    def __init__(
        self,
        scheduler: Scheduler,
        registry: ExtensionRegistry,
        breaker: CircuitBreaker,
    ) -> None:
        self._scheduler = scheduler
        self._registry = registry
        self._breaker = breaker
        self._current: dict[str, tuple[ProviderEntry, PeriodicTask]] = {}

    async def sync(self) -> None:
        """插件加载/重载/停用后调用：移除已失效的任务，登记新任务。

        以 ProviderEntry 对象身份判断变化——插件因配置变更重载后会登记新的
        entry，旧任务随之替换为绑定新插件实例的任务。
        """
        entries = self._registry.providers(points.SCHEDULED_TASK)
        for task_id, (entry, task) in list(self._current.items()):
            if entries.get(task_id) is not entry:
                del self._current[task_id]
                await self._scheduler.remove(task)
        for task_id, entry in entries.items():
            if task_id in self._current:
                continue
            new_task = self._build(task_id, entry)
            if new_task is not None:
                self._current[task_id] = (entry, new_task)
                self._scheduler.add(new_task)

    def _build(self, task_id: str, entry: ProviderEntry) -> PeriodicTask | None:
        plugin_id = entry.plugin_id
        try:
            spec: ScheduledTask = entry.factory()
            spec_run, interval_src = spec.run, spec.interval
            initial_delay = float(spec.initial_delay)
            enabled = spec.enabled or (lambda: True)

            def read_interval() -> float:
                src = interval_src
                return float(src() if callable(src) else src)

            # 间隔由插件代码给出，只在受保护的 run() 里读取；调度器拿到的是
            # 已校验的值，插件出错不会打断调度循环
            interval = read_interval()
        except Exception as e:
            reason = f"{points.SCHEDULED_TASK} {task_id}: {type(e).__name__}: {e}"
            logger.warning("[Plugin:%s] 定时任务创建失败：%s", plugin_id, reason)
            self._breaker.record_failure(plugin_id, reason)
            return None

        async def run() -> None:
            # enabled 与 interval 每轮重新读取（ScheduledTask 契约）；调度器只在
            # 启动时读 enabled，故任务总是启动，停用时空转跳过
            nonlocal interval
            try:
                ran = enabled()
                if ran:
                    await spec_run()
                interval = read_interval()
            except Exception as e:
                reason = f"定时任务 {task_id}: {type(e).__name__}: {e}"
                logger.warning("[Plugin:%s] %s", plugin_id, reason)
                self._breaker.record_failure(plugin_id, reason)
                return
            if ran:
                self._breaker.record_success(plugin_id)

        return PeriodicTask(
            name=f"plugin:{plugin_id}:{task_id}",
            run=run,
            interval=lambda: interval,
            initial_delay=initial_delay,
        )

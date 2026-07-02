"""通用周期任务调度器。

``PeriodicTask`` 把「运行一次 tick，然后等待一个间隔」的循环抽象出来，替代
原先四个手写的 Thread 混入类。``Scheduler`` 负责批量启停这些任务。
"""

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class PeriodicTask:
    """A single asyncio loop that runs ``run`` then waits ``interval`` seconds.

    Semantics mirror the original hand-written loops:

    * ``initial_delay > 0`` waits before the first tick (offset/calendar loops).
    * otherwise the body runs immediately, then waits (rss/rename loops).
    * ``interval`` and ``enabled`` are callables read live each time, so a
      settings change is picked up without rebuilding the task.
    * an exception raised inside a tick is logged and the loop continues.
    """

    def __init__(
        self,
        name: str,
        run: Callable[[], Awaitable[None]],
        interval: Callable[[], float],
        initial_delay: float = 0.0,
        enabled: Callable[[], bool] = lambda: True,
    ) -> None:
        self._name = name
        self._run = run
        self._interval = interval
        self._initial_delay = initial_delay
        self._enabled = enabled
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        return self._enabled()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        """Create the asyncio task. Idempotent while already running."""
        if self.running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name=f"periodic:{self._name}")

    async def _loop(self) -> None:
        try:
            if self._initial_delay > 0:
                if await self._wait(self._initial_delay):
                    return
            while not self._stop_event.is_set():
                try:
                    await self._run()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error("[%s] Error during tick: %s", self._name, e)
                if await self._wait(self._interval()):
                    return
        except asyncio.CancelledError:
            pass

    async def _wait(self, timeout: float) -> bool:
        """Sleep up to ``timeout`` seconds. Return True if a stop was requested."""
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def stop(self) -> None:
        """Signal, cancel, and await the task. Idempotent."""
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None


class Scheduler:
    """Owns a fixed set of :class:`PeriodicTask` and starts/stops them together."""

    def __init__(self, tasks: list[PeriodicTask]) -> None:
        self._tasks = tasks
        self._running = False

    @property
    def tasks(self) -> list[PeriodicTask]:
        return self._tasks

    @property
    def running(self) -> bool:
        return self._running

    def start_all(self) -> None:
        """Start every task whose ``enabled()`` currently returns True."""
        for task in self._tasks:
            if task.enabled:
                task.start()
        self._running = True

    async def stop_all(self) -> None:
        await asyncio.gather(*(task.stop() for task in self._tasks))
        self._running = False

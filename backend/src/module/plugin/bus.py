"""进程内事件总线。

每个订阅者有独立的有界队列与 worker 任务：同一订阅者按发布顺序处理事件，
单个订阅者变慢、抛错或超时都不会阻塞发布方和其他订阅者。``publish`` 是同步
调用，只负责入队。
"""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable

from ab_sdk import Event

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None] | None]
ErrorCallback = Callable[[str, str], None]

ALL_EVENTS = "*"
DEFAULT_HANDLER_TIMEOUT = 30.0
DEFAULT_QUEUE_SIZE = 1000


class _Subscriber:
    def __init__(
        self,
        kind: str,
        handler: Handler,
        owner: str | None,
        timeout: float,
        queue_size: int,
        on_error: ErrorCallback | None,
    ) -> None:
        self.kind = kind
        self.handler = handler
        self.owner = owner
        self._timeout = timeout
        self._on_error = on_error
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)
        self._worker: asyncio.Task | None = None

    def matches(self, event: Event) -> bool:
        return self.kind == ALL_EVENTS or self.kind == event.kind

    def offer(self, event: Event) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                "[EventBus] Subscriber queue full (owner=%s, kind=%s); dropped %s",
                self.owner,
                self.kind,
                event.kind,
            )
            return
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(
                self._run(), name=f"event-subscriber:{self.owner}:{self.kind}"
            )

    async def _run(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                result = self.handler(event)
                if inspect.isawaitable(result):
                    await asyncio.wait_for(result, self._timeout)
            except Exception as e:
                reason = (
                    f"timed out after {self._timeout}s"
                    if isinstance(e, TimeoutError)
                    else f"{type(e).__name__}: {e}"
                )
                logger.warning(
                    "[EventBus] Handler for %s (owner=%s) failed: %s",
                    event.kind,
                    self.owner,
                    reason,
                )
                if self._on_error is not None and self.owner is not None:
                    self._on_error(self.owner, reason)
            finally:
                self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    async def close(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None


class EventBus:
    def __init__(
        self,
        *,
        handler_timeout: float = DEFAULT_HANDLER_TIMEOUT,
        queue_size: int = DEFAULT_QUEUE_SIZE,
        on_error: ErrorCallback | None = None,
    ) -> None:
        self._timeout = handler_timeout
        self._queue_size = queue_size
        self._subscribers: list[_Subscriber] = []
        # 订阅者失败回调（owner, reason），宿主用它驱动插件熔断
        self.on_error = on_error

    def subscribe(
        self, kind: str, handler: Handler, *, owner: str | None = None
    ) -> Callable[[], None]:
        sub = _Subscriber(
            kind,
            handler,
            owner,
            self._timeout,
            self._queue_size,
            self._report_error,
        )
        self._subscribers.append(sub)

        def unsubscribe() -> None:
            if sub in self._subscribers:
                self._subscribers.remove(sub)
                asyncio.ensure_future(sub.close())

        return unsubscribe

    def publish(self, event: Event) -> None:
        for sub in list(self._subscribers):
            if sub.matches(event):
                sub.offer(event)

    async def drain(self) -> None:
        """等待当前已入队的事件全部处理完（测试与关闭流程使用）。"""
        await asyncio.gather(*(sub.join() for sub in list(self._subscribers)))

    async def close_owner(self, owner: str) -> None:
        subs = [s for s in self._subscribers if s.owner == owner]
        for sub in subs:
            self._subscribers.remove(sub)
        await asyncio.gather(*(sub.close() for sub in subs))

    async def close(self) -> None:
        subs, self._subscribers = self._subscribers, []
        await asyncio.gather(*(sub.close() for sub in subs))

    def _report_error(self, owner: str, reason: str) -> None:
        if self.on_error is not None:
            self.on_error(owner, reason)

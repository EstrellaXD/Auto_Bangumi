"""进程内事件总线。

每个订阅者有独立的有界队列与 worker 任务：同一订阅者按发布顺序处理事件，
单个订阅者变慢、抛错或超时都不会阻塞发布方和其他订阅者。``publish`` 是同步
调用，只负责入队。
"""

import asyncio
import contextlib
import inspect
import logging
from collections.abc import Awaitable, Callable

from ab_sdk import Event

logger = logging.getLogger(__name__)

Handler = Callable[[Event], Awaitable[None] | None]
ErrorCallback = Callable[[str, str], None]
SuccessCallback = Callable[[str], None]

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
        on_success: SuccessCallback | None,
    ) -> None:
        self.kind = kind
        self.handler = handler
        self.owner = owner
        self._timeout = timeout
        self._on_error = on_error
        self._on_success = on_success
        self._queue: asyncio.Queue[tuple[Event, asyncio.Future[bool] | None]] = (
            asyncio.Queue(maxsize=queue_size)
        )
        self._worker: asyncio.Task | None = None

    def matches(self, event: Event) -> bool:
        return self.kind == ALL_EVENTS or self.kind == event.kind

    def offer(self, event: Event, receipt: asyncio.Future[bool] | None = None) -> None:
        try:
            self._queue.put_nowait((event, receipt))
        except asyncio.QueueFull:
            if receipt is not None:
                receipt.set_result(False)
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
            event, receipt = await self._queue.get()
            succeeded = False
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
            else:
                succeeded = True
                if self._on_success is not None and self.owner is not None:
                    self._on_success(self.owner)
            finally:
                if receipt is not None and not receipt.done():
                    receipt.set_result(succeeded)
                self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()

    async def close(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker
            self._worker = None
        while not self._queue.empty():
            _, receipt = self._queue.get_nowait()
            if receipt is not None and not receipt.done():
                receipt.set_result(False)
            self._queue.task_done()


class EventBus:
    def __init__(
        self,
        *,
        handler_timeout: float = DEFAULT_HANDLER_TIMEOUT,
        queue_size: int = DEFAULT_QUEUE_SIZE,
        on_error: ErrorCallback | None = None,
        on_success: SuccessCallback | None = None,
    ) -> None:
        self._timeout = handler_timeout
        self._queue_size = queue_size
        self._subscribers: list[_Subscriber] = []
        # 退订时异步关闭订阅者的任务；事件循环只弱引用任务，这里持有强引用防止被 GC
        self._closing: set[asyncio.Future] = set()
        # 订阅者失败 / 成功回调，宿主用它驱动插件熔断（成功时清零连续失败计数）
        self.on_error = on_error
        self.on_success = on_success

    def subscribe(
        self,
        kind: str,
        handler: Handler,
        *,
        owner: str | None = None,
        timeout: float | None = None,
    ) -> Callable[[], None]:
        sub = _Subscriber(
            kind,
            handler,
            owner,
            timeout if timeout is not None else self._timeout,
            self._queue_size,
            self._report_error,
            self._report_success,
        )
        self._subscribers.append(sub)

        def unsubscribe() -> None:
            if sub in self._subscribers:
                self._subscribers.remove(sub)
                task = asyncio.ensure_future(sub.close())
                self._closing.add(task)
                task.add_done_callback(self._closing.discard)

        return unsubscribe

    def publish(self, event: Event) -> None:
        for sub in list(self._subscribers):
            if sub.matches(event):
                sub.offer(event)

    async def publish_confirmed(self, event: Event) -> bool:
        """持久 outbox 使用：按各订阅者原队列顺序投递，全部处理成功才确认。

        失败或队列满返回 False，调用方保留记录重试。普通 publish 的行为不变。
        """
        receipts = []
        for sub in list(self._subscribers):
            if sub.matches(event):
                receipt = asyncio.get_running_loop().create_future()
                sub.offer(event, receipt)
                receipts.append(receipt)
        return all(await asyncio.gather(*receipts))

    async def drain(self) -> None:
        """等待当前已入队的事件全部处理完（测试使用）。"""
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

    def _report_success(self, owner: str) -> None:
        if self.on_success is not None:
            self.on_success(owner)

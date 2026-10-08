"""钩子与 Provider 的调用：优先级排序、超时、错误隔离与按插件熔断。"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any

from ab_sdk import Verdict

from .registry import ExtensionRegistry, HookEntry

logger = logging.getLogger(__name__)

DEFAULT_HOOK_TIMEOUT = 30.0
DEFAULT_FAILURE_THRESHOLD = 5

TripCallback = Callable[[str, str], None]


class CircuitBreaker:
    """同一插件连续失败 ``threshold`` 次后触发 ``on_trip``（只触发一次）。

    任意一次成功调用清零计数；被触发后由宿主禁用该插件，重新启用时调用
    :meth:`reset`。
    """

    def __init__(
        self,
        threshold: int = DEFAULT_FAILURE_THRESHOLD,
        on_trip: TripCallback | None = None,
    ) -> None:
        self._threshold = threshold
        self._failures: dict[str, int] = {}
        self._tripped: set[str] = set()
        self.on_trip = on_trip

    def record_success(self, plugin_id: str) -> None:
        self._failures.pop(plugin_id, None)

    def record_failure(self, plugin_id: str, reason: str) -> None:
        if plugin_id in self._tripped:
            return
        count = self._failures.get(plugin_id, 0) + 1
        self._failures[plugin_id] = count
        if count >= self._threshold:
            self._tripped.add(plugin_id)
            if self.on_trip is not None:
                self.on_trip(
                    plugin_id, f"连续失败 {count} 次，已自动禁用；最后一次：{reason}"
                )

    def reset(self, plugin_id: str) -> None:
        self._failures.pop(plugin_id, None)
        self._tripped.discard(plugin_id)


class HookRunner:
    def __init__(
        self,
        registry: ExtensionRegistry,
        breaker: CircuitBreaker,
        *,
        order: Callable[[str], list[str]] = lambda point: [],
        default_timeout: float = DEFAULT_HOOK_TIMEOUT,
    ) -> None:
        self._registry = registry
        self._breaker = breaker
        self._order = order
        self._default_timeout = default_timeout

    async def filter(self, point: str, *args: Any, **kwargs: Any) -> Verdict:
        """依次执行 filter 钩子，第一个拒绝即返回；全部通过返回 ``Verdict.ok()``。"""
        fail_open = self._registry.point(point).fail_open
        for entry in self._registry.hooks(point, self._order(point)):
            ok, result = await self._call(entry, point, args, kwargs)
            if not ok:
                if fail_open:
                    continue
                return Verdict.reject(f"插件 {entry.plugin_id} 执行失败")
            verdict = _as_verdict(result)
            if verdict is None:
                logger.warning(
                    "[Plugin:%s] %s 返回了无效结果 %r，按放行处理",
                    entry.plugin_id,
                    point,
                    result,
                )
                continue
            if not verdict.accept:
                return verdict
        return Verdict.ok()

    async def transform(self, point: str, value: Any, *args: Any, **kwargs: Any) -> Any:
        """把 ``value`` 依次交给 transform 钩子；钩子失败或返回 None 时沿用原值。"""
        for entry in self._registry.hooks(point, self._order(point)):
            ok, result = await self._call(entry, point, (value, *args), kwargs)
            if ok and result is not None:
                value = result
        return value

    async def _call(
        self,
        entry: HookEntry,
        point: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> tuple[bool, Any]:
        timeout = entry.timeout or self._default_timeout
        try:
            result = entry.func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout)
        except Exception as e:
            reason = (
                f"{point} 超时（{timeout}s）"
                if isinstance(e, TimeoutError)
                else f"{point}: {type(e).__name__}: {e}"
            )
            logger.warning("[Plugin:%s] 钩子失败：%s", entry.plugin_id, reason)
            self._breaker.record_failure(entry.plugin_id, reason)
            return False, None
        self._breaker.record_success(entry.plugin_id)
        return True, result


def _as_verdict(result: Any) -> Verdict | None:
    if isinstance(result, Verdict):
        return result
    if isinstance(result, bool):
        return Verdict(result)
    return None

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
# 校验插件返回值（None 不经校验，表示不修改）
Check = Callable[[Any], bool]


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

    def has_hooks(self, point: str) -> bool:
        return self._registry.has_hooks(point)

    async def transform(
        self,
        point: str,
        value: Any,
        *args: Any,
        expect: type | tuple[type, ...] | None = None,
        check: Check | None = None,
        **kwargs: Any,
    ) -> Any:
        """把 ``value`` 依次交给 transform 钩子；钩子失败或返回 None 时沿用原值。

        ``expect`` 给出时，返回值不是该类型的结果按钩子失败处理（计入熔断）；
        ``check`` 再校验字段取值。避免一个插件的错误返回值传给后续钩子和宿主。
        """

        def valid(result: Any) -> bool:
            return (expect is None or isinstance(result, expect)) and (
                check is None or check(result)
            )

        for entry in self._registry.hooks(point, self._order(point)):
            ok, result = await self._call(entry, point, (value, *args), kwargs, valid)
            if not ok or result is None:
                continue
            value = result
        return value

    async def call_provider(
        self,
        plugin_id: str,
        point: str,
        func: Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        check: Check | None = None,
    ) -> tuple[bool, Any]:
        """以钩子同样的超时与熔断规则调用插件 Provider 的方法。

        返回 ``(是否成功, 结果)``；失败（含 ``check`` 不通过）已记录日志并计入熔断。
        """
        entry = HookEntry(plugin_id, func, 0, timeout)
        return await self._call(entry, point, args, {}, check)

    async def _call(
        self,
        entry: HookEntry,
        point: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        check: Check | None = None,
    ) -> tuple[bool, Any]:
        timeout = entry.timeout or self._default_timeout
        try:
            result = entry.func(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout)
            # 返回值校验在记成功之前：无效结果必须计入熔断，而不是先清零再计一次
            if result is not None and check is not None and not check(result):
                raise TypeError(f"返回了无效结果 {type(result).__name__}，已忽略")
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

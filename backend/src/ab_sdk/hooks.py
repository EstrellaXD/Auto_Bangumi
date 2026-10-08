"""扩展声明：``@hook`` 标记钩子方法，``@provider`` 标记 Provider 工厂方法，
``@subscribe`` 标记事件订阅方法。

装饰器只在函数上打标记，不做注册；插件加载时由宿主扫描 Plugin 类的成员，
把标记过的方法绑定到插件实例后登记到注册表。
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

HOOK_ATTR = "__ab_hook__"
PROVIDER_ATTR = "__ab_provider__"
SUBSCRIBE_ATTR = "__ab_subscribe__"


@dataclass(frozen=True, slots=True)
class HookSpec:
    point: str
    priority: int
    timeout: float | None


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    point: str
    id: str


@dataclass(frozen=True, slots=True)
class SubscribeSpec:
    kind: str
    timeout: float | None = None


@dataclass(frozen=True, slots=True)
class Verdict:
    """Filter 钩子的返回值。``reason`` 用于日志与 UI 展示被拒原因。"""

    accept: bool
    reason: str | None = None

    @classmethod
    def ok(cls) -> "Verdict":
        return cls(True)

    @classmethod
    def reject(cls, reason: str) -> "Verdict":
        return cls(False, reason)


def hook(point: str, *, priority: int = 100, timeout: float | None = None):
    """把方法声明为某个扩展点的钩子。

    ``point`` 必须是宿主声明的 filter / transform 扩展点，否则插件加载失败。
    同一扩展点上的钩子按 ``priority`` 升序执行，相同优先级按插件 id 排序；
    用户可在 ``plugins.hook_order`` 中显式指定顺序。``timeout`` 覆盖宿主默认
    超时（秒）。

    - filter 钩子返回 :class:`Verdict`（或 bool），任一拒绝即短路。
    - transform 钩子接收上一个钩子的结果并返回新值；返回 None 表示不修改。
    """

    def mark(func: F) -> F:
        setattr(func, HOOK_ATTR, HookSpec(point, priority, timeout))
        return func

    return mark


def provider(point: str, *, id: str):
    """把方法声明为某个 Provider 扩展点的实现工厂。

    被装饰的方法不接受参数（``self`` 除外），返回该扩展点约定的实现对象；
    宿主在需要时调用它，可通过 ``self.ctx`` 读取插件配置。
    """

    def mark(func: F) -> F:
        setattr(func, PROVIDER_ATTR, ProviderSpec(point, id))
        return func

    return mark


def subscribe(kind: str, *, timeout: float | None = None):
    """把方法声明为事件订阅者，参数为事件对象。

    订阅者在独立队列中按发布顺序异步执行，失败或超时不影响发布方。
    ``kind`` 为 ``"*"`` 时接收全部事件。``timeout`` 覆盖宿主默认的单个事件
    处理超时（秒），适合复制大文件等耗时操作。
    """

    def mark(func: F) -> F:
        setattr(func, SUBSCRIBE_ATTR, SubscribeSpec(kind, timeout))
        return func

    return mark

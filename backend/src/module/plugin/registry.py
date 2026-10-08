"""扩展点注册表：宿主声明扩展点，插件在其上登记 Provider 与钩子。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

PointKind = Literal["provider", "filter", "transform"]


class RegistryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExtensionPoint:
    name: str
    kind: PointKind
    description: str = ""
    # 仅 filter：钩子出错/超时时是否放行（True）还是视为拒绝（False）
    fail_open: bool = True
    # 仅 provider：True 时 Provider id 只需在插件内唯一（宿主对外暴露时会加
    # 插件 id 前缀，如插件路由、MCP 工具），注册表按 ``<plugin_id>/<id>`` 存储
    scoped: bool = False


@dataclass(frozen=True, slots=True)
class HookEntry:
    plugin_id: str
    func: Callable[..., Any]
    priority: int
    timeout: float | None


@dataclass(frozen=True, slots=True)
class ProviderEntry:
    plugin_id: str
    id: str
    factory: Callable[[], Any]


class ExtensionRegistry:
    def __init__(self) -> None:
        self._points: dict[str, ExtensionPoint] = {}
        self._hooks: dict[str, list[HookEntry]] = {}
        self._providers: dict[str, dict[str, ProviderEntry]] = {}

    # ------------------------------------------------------------ points

    def declare(self, point: ExtensionPoint) -> None:
        existing = self._points.get(point.name)
        if existing is not None and existing != point:
            raise RegistryError(f"扩展点 {point.name} 已以不同定义声明")
        self._points[point.name] = point

    def point(self, name: str) -> ExtensionPoint:
        try:
            return self._points[name]
        except KeyError:
            raise RegistryError(f"未知扩展点：{name}") from None

    # ------------------------------------------------------------ registration

    def add_hook(self, point_name: str, entry: HookEntry) -> None:
        point = self.point(point_name)
        if point.kind == "provider":
            raise RegistryError(f"{point_name} 是 Provider 扩展点，请使用 @provider")
        self._hooks.setdefault(point_name, []).append(entry)

    def add_provider(self, point_name: str, entry: ProviderEntry) -> None:
        point = self.point(point_name)
        if point.kind != "provider":
            raise RegistryError(f"{point_name} 是 {point.kind} 扩展点，请使用 @hook")
        slot = self._providers.setdefault(point_name, {})
        key = f"{entry.plugin_id}/{entry.id}" if point.scoped else entry.id
        owner = slot.get(key)
        if owner is not None:
            raise RegistryError(
                f"{point_name} 的 Provider id {entry.id!r} 已被插件 "
                f"{owner.plugin_id} 占用"
            )
        slot[key] = entry

    def remove_plugin(self, plugin_id: str) -> None:
        for name, entries in self._hooks.items():
            self._hooks[name] = [e for e in entries if e.plugin_id != plugin_id]
        for slot in self._providers.values():
            for pid in [k for k, e in slot.items() if e.plugin_id == plugin_id]:
                del slot[pid]

    # ------------------------------------------------------------ lookup

    def hooks(self, point_name: str, order: list[str] | None = None) -> list[HookEntry]:
        """按执行顺序返回钩子：``order`` 中列出的插件按列出顺序排最前，
        其余按 (priority, plugin_id) 排序。"""
        self.point(point_name)
        rank = {pid: i for i, pid in enumerate(order or [])}
        return sorted(
            self._hooks.get(point_name, []),
            key=lambda e: (rank.get(e.plugin_id, len(rank)), e.priority, e.plugin_id),
        )

    def providers(self, point_name: str) -> dict[str, ProviderEntry]:
        """按 Provider id 索引；``scoped`` 扩展点的键为 ``<plugin_id>/<id>``。"""
        self.point(point_name)
        return dict(self._providers.get(point_name, {}))

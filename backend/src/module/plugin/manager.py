"""插件生命周期：发现 → 加载 → 注册扩展 → setup → 运行 → teardown。"""

import asyncio
import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from ab_sdk import SDK_VERSION, Plugin, PluginDisabled, PluginLoaded
from ab_sdk.hooks import HOOK_ATTR, PROVIDER_ATTR, SUBSCRIBE_ATTR

from .bus import EventBus
from .context import PLUGIN_DATA_ROOT, HostPluginContext
from .loader import DiscoveryError, PluginCandidate, PluginLoadError, discover
from .manifest import PluginUi
from .registry import ExtensionRegistry, HookEntry, ProviderEntry
from .runner import CircuitBreaker, HookRunner

logger = logging.getLogger(__name__)

PluginState = Literal["active", "disabled", "error"]
DEFAULT_SETUP_TIMEOUT = 30.0

Discover = Callable[[], tuple[list[PluginCandidate], list[DiscoveryError]]]


@dataclass(frozen=True)
class PluginStatus:
    id: str
    name: str
    version: str
    source: str
    signed: bool
    state: PluginState
    description: str = ""
    permissions: list[str] = field(default_factory=list)
    error: str | None = None
    enabled: bool = False
    # config_model 的 JSON Schema；插件代码加载过一次后才有（不为取 schema
    # 去执行未启用插件的代码），未声明 config_model 时为 None
    config_schema: dict[str, Any] | None = None


@dataclass
class _Active:
    candidate: PluginCandidate
    instance: Plugin
    snapshot: str


class PluginManager:
    def __init__(
        self,
        settings_obj,
        *,
        registry: ExtensionRegistry | None = None,
        discover_fn: Discover = discover,
        setup_timeout: float = DEFAULT_SETUP_TIMEOUT,
        data_root: Path = PLUGIN_DATA_ROOT,
    ) -> None:
        self._settings = settings_obj
        self._discover = discover_fn
        self._setup_timeout = setup_timeout
        self._data_root = data_root
        self.registry = registry if registry is not None else ExtensionRegistry()
        self.breaker = CircuitBreaker(on_trip=self._on_trip)
        self.bus = EventBus(on_error=self.breaker.record_failure)
        self.runner = HookRunner(
            self.registry,
            self.breaker,
            order=lambda point: self._settings.plugins.hook_order.get(point, []),
        )
        self._candidates: dict[str, PluginCandidate] = {}
        self._active: dict[str, _Active] = {}
        # 失败记录：(失败时的配置快照, 原因)。配置未变时不重试，避免每次保存
        # 设置都把同一个坏插件重新加载一遍。
        self._failed: dict[str, tuple[str, str]] = {}
        self._models: dict[str, type[BaseModel] | None] = {}
        self._lock = asyncio.Lock()
        self._pending: set[asyncio.Task] = set()
        # 插件集合变化后的回调（宿主据此同步插件定时任务等派生状态）
        self.on_change: Callable[[], Awaitable[None]] | None = None

    # ------------------------------------------------------------ lifecycle

    async def start(self) -> None:
        async with self._lock:
            self._rediscover()
            for candidate in self._candidates.values():
                if self._blocked_reason(candidate) is None:
                    await self._activate(candidate)
        logger.info(
            "[Plugin] %d 个插件已启用，共发现 %d 个",
            len(self._active),
            len(self._candidates),
        )
        await self._notify_change()

    async def stop(self) -> None:
        for task in list(self._pending):
            task.cancel()
        await asyncio.gather(*self._pending, return_exceptions=True)
        async with self._lock:
            for plugin_id in list(self._active):
                await self._deactivate(plugin_id)
        await self.bus.close()

    async def apply_settings(self) -> None:
        """配置变更后调用：停用被关闭/配置变化/已消失的插件，启用新开启的插件。"""
        async with self._lock:
            self._rediscover()
            for plugin_id, active in list(self._active.items()):
                candidate = self._candidates.get(plugin_id)
                if (
                    candidate is None
                    or self._blocked_reason(candidate) is not None
                    or self._snapshot(plugin_id) != active.snapshot
                ):
                    await self._deactivate(plugin_id)
            for plugin_id, candidate in self._candidates.items():
                if plugin_id in self._active or self._blocked_reason(candidate):
                    continue
                failed = self._failed.get(plugin_id)
                if failed is not None and failed[0] == self._snapshot(plugin_id):
                    continue
                await self._activate(candidate)
        await self._notify_change()

    # ------------------------------------------------------------ status

    def statuses(self) -> list[PluginStatus]:
        result = []
        for plugin_id in sorted(self._candidates):
            candidate = self._candidates[plugin_id]
            manifest = candidate.manifest
            state: PluginState
            if plugin_id in self._active:
                state, error = "active", None
            elif plugin_id in self._failed:
                state, error = "error", self._failed[plugin_id][1]
            else:
                state, error = "disabled", self._blocked_reason(candidate)
            result.append(
                PluginStatus(
                    id=plugin_id,
                    name=manifest.name,
                    version=manifest.version,
                    source=candidate.source,
                    signed=candidate.signed,
                    state=state,
                    description=manifest.description,
                    permissions=list(manifest.permissions),
                    error=error,
                    enabled=self._enabled(candidate),
                    config_schema=self._schema(plugin_id),
                )
            )
        return result

    def ui_slots(self) -> list[tuple[str, PluginUi]]:
        """已启用插件声明的前端挂载点，按插件 id 排序。"""
        return [
            (plugin_id, ui)
            for plugin_id, active in sorted(self._active.items())
            for ui in active.candidate.manifest.ui
        ]

    def web_dir(self, plugin_id: str) -> Path | None:
        """已启用插件的 ``web/`` 目录；未启用或没有该目录时为 None。"""
        active = self._active.get(plugin_id)
        if active is None or active.candidate.root is None:
            return None
        web = active.candidate.root / "web"
        return web if web.is_dir() else None

    def validate_options(self, plugin_id: str, options: dict[str, Any]) -> None:
        """按插件的 config_model 校验配置（插件代码未加载过时不校验）。

        Raises:
            pydantic.ValidationError: 配置不合法。
        """
        model = self._models.get(plugin_id)
        if model is not None:
            model.model_validate(options)

    # ------------------------------------------------------------ internals

    def _schema(self, plugin_id: str) -> dict[str, Any] | None:
        model = self._models.get(plugin_id)
        return model.model_json_schema() if model is not None else None

    def _rediscover(self) -> None:
        # 清单错误已在 discover() 中记录日志
        candidates, _ = self._discover()
        self._candidates = {c.manifest.id: c for c in candidates}
        for plugin_id in [p for p in self._failed if p not in self._candidates]:
            del self._failed[plugin_id]

    def _blocked_reason(self, candidate: PluginCandidate) -> str | None:
        """插件不应运行的原因；None 表示应启用。"""
        conf = self._settings.plugins
        if not self._enabled(candidate):
            return "未启用"
        if not candidate.signed and not conf.allow_unsigned:
            return "未签名插件需要开启 plugins.allow_unsigned"
        return None

    def _enabled(self, candidate: PluginCandidate) -> bool:
        """启用开关；未设置时内置插件默认启用（清单 ``default_enabled = false``
        的除外），其它来源默认禁用。"""
        default = candidate.source == "builtin" and candidate.manifest.default_enabled
        return self._settings.plugins.enabled.get(candidate.manifest.id, default)

    def _snapshot(self, plugin_id: str) -> str:
        conf = self._settings.plugins
        return json.dumps(
            {
                "enabled": conf.enabled.get(plugin_id),
                "options": conf.options.get(plugin_id, {}),
            },
            sort_keys=True,
            default=str,
        )

    async def _activate(self, candidate: PluginCandidate) -> None:
        manifest = candidate.manifest
        plugin_id = manifest.id
        snapshot = self._snapshot(plugin_id)
        try:
            if not manifest.sdk_compatible():
                raise PluginLoadError(
                    f"需要 ab_sdk {manifest.sdk}，当前为 {SDK_VERSION}"
                )
            cls = candidate.load()
            self._models[plugin_id] = cls.config_model
            config = self._validate_config(cls, plugin_id)
            ctx = HostPluginContext(plugin_id, config, self.bus, self._data_root)
            instance = cls(ctx)
            self._register(plugin_id, instance)
            await asyncio.wait_for(instance.setup(), self._setup_timeout)
        except Exception as e:
            reason = (
                f"setup 超时（{self._setup_timeout}s）"
                if isinstance(e, TimeoutError)
                else str(e) or type(e).__name__
            )
            self.registry.remove_plugin(plugin_id)
            await self.bus.close_owner(plugin_id)
            candidate.unload()
            self._failed[plugin_id] = (snapshot, reason)
            logger.error("[Plugin:%s] 加载失败：%s", plugin_id, reason)
            self.bus.publish(PluginDisabled(plugin_id=plugin_id, reason=reason))
            return
        self._failed.pop(plugin_id, None)
        self.breaker.reset(plugin_id)
        self._active[plugin_id] = _Active(candidate, instance, snapshot)
        logger.info(
            "[Plugin:%s] 已加载 %s（%s）", plugin_id, manifest.version, candidate.source
        )
        self.bus.publish(PluginLoaded(plugin_id=plugin_id, version=manifest.version))

    def _validate_config(
        self, cls: type[Plugin[Any]], plugin_id: str
    ) -> BaseModel | None:
        options = self._settings.plugins.options.get(plugin_id, {})
        if cls.config_model is None:
            if options:
                logger.warning(
                    "[Plugin:%s] 插件未声明 config_model，忽略配置 %s",
                    plugin_id,
                    sorted(options),
                )
            return None
        return cls.config_model.model_validate(options)

    def _register(self, plugin_id: str, instance: Plugin) -> None:
        for name, member in inspect.getmembers(type(instance), callable):
            hook_spec = getattr(member, HOOK_ATTR, None)
            provider_spec = getattr(member, PROVIDER_ATTR, None)
            subscribe_spec = getattr(member, SUBSCRIBE_ATTR, None)
            if not (hook_spec or provider_spec or subscribe_spec):
                continue
            bound = getattr(instance, name)
            if hook_spec is not None:
                self.registry.add_hook(
                    hook_spec.point,
                    HookEntry(plugin_id, bound, hook_spec.priority, hook_spec.timeout),
                )
            if provider_spec is not None:
                self.registry.add_provider(
                    provider_spec.point,
                    ProviderEntry(plugin_id, provider_spec.id, bound),
                )
            if subscribe_spec is not None:
                self.bus.subscribe(
                    subscribe_spec.kind,
                    bound,
                    owner=plugin_id,
                    timeout=subscribe_spec.timeout,
                )

    async def _deactivate(self, plugin_id: str) -> None:
        active = self._active.pop(plugin_id, None)
        if active is None:
            return
        self.registry.remove_plugin(plugin_id)
        await self.bus.close_owner(plugin_id)
        try:
            await asyncio.wait_for(active.instance.teardown(), self._setup_timeout)
        except Exception as e:
            logger.warning("[Plugin:%s] teardown 失败：%s", plugin_id, e)
        active.candidate.unload()
        logger.info("[Plugin:%s] 已停用", plugin_id)

    def _on_trip(self, plugin_id: str, reason: str) -> None:
        task = asyncio.create_task(self._disable(plugin_id, reason))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def _disable(self, plugin_id: str, reason: str) -> None:
        async with self._lock:
            active = self._active.get(plugin_id)
            if active is None:
                return
            await self._deactivate(plugin_id)
            self._failed[plugin_id] = (active.snapshot, reason)
        logger.error("[Plugin:%s] %s", plugin_id, reason)
        self.bus.publish(PluginDisabled(plugin_id=plugin_id, reason=reason))
        await self._notify_change()

    async def _notify_change(self) -> None:
        if self.on_change is None:
            return
        try:
            await self.on_change()
        except Exception:
            logger.exception("[Plugin] 插件变更回调失败")

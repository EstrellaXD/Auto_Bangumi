"""进程级扩展注册表，以及宿主自带实现的登记。

AB 自己的下载器、通知渠道与搜索站点和第三方插件走同一个注册表、同一套
``ab_sdk`` 契约，只是以 ``core`` 身份登记：它们随进程存在，不经插件管理器
加载，因此不能被禁用，也不会因插件故障被熔断。

注册表在首次访问时初始化，不依赖 AppContext——下载门面等模块级代码在
任何上下文里都能解析 Provider。
"""

import logging
from typing import Any

from ab_sdk import Event, points
from ab_sdk.downloader import DownloaderConnection

from .bus import EventBus
from .registry import ExtensionPoint, ExtensionRegistry, ProviderEntry
from .runner import HookRunner

logger = logging.getLogger(__name__)

CORE = "core"

POINTS = (
    ExtensionPoint(points.DOWNLOADER, "provider", "下载器后端（downloader.type）"),
    ExtensionPoint(
        points.NOTIFIER, "provider", "通知渠道（notification.providers[].type）"
    ),
    ExtensionPoint(points.LLM_PROVIDER, "provider", "LLM 解析提供商（llm.provider）"),
    ExtensionPoint(points.SEARCH_SITE, "provider", "搜索站点"),
    ExtensionPoint(points.SCHEDULED_TASK, "provider", "定时任务"),
    # --- P5 events/api ---
    ExtensionPoint(
        points.API_ROUTER,
        "provider",
        "插件 REST 路由（/api/v1/plugins/<id>/）",
        scoped=True,
    ),
    ExtensionPoint(points.MCP_TOOL, "provider", "MCP 工具", scoped=True),
    ExtensionPoint(points.MCP_RESOURCE, "provider", "MCP 资源", scoped=True),
    ExtensionPoint(points.MESSAGE_TEMPLATE, "transform", "系统事件通知文案"),
)

_registry: ExtensionRegistry | None = None
# 进程级事件总线与钩子执行器，由 AppContext 在构造时设置（即 PluginManager
# 持有的那一份）；未设置时（单元测试、脚本）发布事件与执行钩子均为空操作
_bus: EventBus | None = None
_runner: HookRunner | None = None


def get_registry() -> ExtensionRegistry:
    global _registry
    if _registry is None:
        registry = ExtensionRegistry()
        for point in POINTS:
            registry.declare(point)
        _register_core(registry)
        _registry = registry
    return _registry


def provider(point: str, provider_id: str) -> Any | None:
    """调用 Provider 工厂取得实现；未登记时返回 None。"""
    entry = get_registry().providers(point).get(provider_id)
    return entry.factory() if entry is not None else None


def plugin_provider_ids(point: str) -> list[str]:
    """由插件（而非 core）提供的 Provider id，供设置页合并到候选列表。"""
    return sorted(
        pid
        for pid, entry in get_registry().providers(point).items()
        if entry.plugin_id != CORE
    )


def _core(registry: ExtensionRegistry, point: str, provider_id: str, impl: Any) -> None:
    registry.add_provider(point, ProviderEntry(CORE, provider_id, lambda: impl))


def _register_core(registry: ExtensionRegistry) -> None:
    # 具体下载器延迟到实际使用时再 import，与原先 if/elif 的懒加载一致
    def qbittorrent(conn: DownloaderConnection):
        from module.downloader.client.qb_downloader import QbDownloader

        return QbDownloader(conn.host, conn.username, conn.password, conn.ssl)

    def aria2(conn: DownloaderConnection):
        from module.downloader.client.aria2_downloader import Aria2Downloader

        return Aria2Downloader(conn.host, conn.username, conn.password)

    def mock(conn: DownloaderConnection):
        from module.downloader.client.mock_downloader import MockDownloader

        return MockDownloader()

    for provider_id, factory in (
        ("qbittorrent", qbittorrent),
        ("aria2", aria2),
        ("mock", mock),
    ):
        _core(registry, points.DOWNLOADER, provider_id, factory)

    from module.notification.providers import PROVIDER_REGISTRY

    for provider_id, provider_cls in PROVIDER_REGISTRY.items():
        _core(registry, points.NOTIFIER, provider_id, provider_cls)


# --- P5 events/api ---------------------------------------------------------


def get_bus() -> EventBus | None:
    return _bus


def set_bus(bus: EventBus | None) -> None:
    global _bus
    _bus = bus


def get_runner() -> HookRunner | None:
    return _runner


def set_runner(runner: HookRunner | None) -> None:
    global _runner
    _runner = runner


def publish(event: Event) -> None:
    """把宿主事件发布到进程级总线；总线未设置时什么也不做。

    发布只负责入队，订阅者的失败不会影响调用方。没有运行中的事件循环时
    （同步上下文）无法投递，记录日志后忽略。
    """
    bus = _bus
    if bus is None:
        return
    try:
        bus.publish(event)
    except RuntimeError:
        logger.debug("[EventBus] 无事件循环，丢弃事件 %s", event.kind)

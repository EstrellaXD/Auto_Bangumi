"""进程级扩展注册表，以及宿主自带实现的登记。

AB 自己的下载器、通知渠道与搜索站点和第三方插件走同一个注册表、同一套
``ab_sdk`` 契约，只是以 ``core`` 身份登记：它们随进程存在，不经插件管理器
加载，因此不能被禁用，也不会因插件故障被熔断。

注册表在首次访问时初始化，不依赖 AppContext——下载门面等模块级代码在
任何上下文里都能解析 Provider。
"""

import logging
from collections.abc import Callable
from typing import Any

from ab_sdk import points
from ab_sdk.downloader import DownloaderConnection

from .registry import ExtensionPoint, ExtensionRegistry, ProviderEntry

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
)

_registry: ExtensionRegistry | None = None


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


def provider_impls(
    point: str, valid: Callable[[Any], bool] = lambda impl: True
) -> dict[str, Any]:
    """调用该扩展点全部 Provider 工厂；工厂出错或产物不合契约（``valid``
    返回 False）的跳过并记录，不连累其它 Provider。"""
    impls: dict[str, Any] = {}
    for provider_id, entry in get_registry().providers(point).items():
        try:
            impl = entry.factory()
            if not valid(impl):
                raise TypeError(f"不合契约的返回值 {impl!r}")
        except Exception as e:
            logger.warning(
                "[Plugin:%s] %s %s 创建失败：%s", entry.plugin_id, point, provider_id, e
            )
            continue
        impls[provider_id] = impl
    return impls


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

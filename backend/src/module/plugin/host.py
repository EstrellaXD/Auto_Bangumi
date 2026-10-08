"""进程级扩展注册表，以及宿主自带实现的登记。

AB 自己的下载器、通知渠道与搜索站点和第三方插件走同一个注册表、同一套
``ab_sdk`` 契约，只是以 ``core`` 身份登记：它们随进程存在，不经插件管理器
加载，因此不能被禁用，也不会因插件故障被熔断。

注册表在首次访问时初始化，不依赖 AppContext——下载门面等模块级代码在
任何上下文里都能解析 Provider。
"""

from typing import Any

from ab_sdk import points
from ab_sdk.downloader import DownloaderConnection

from .registry import ExtensionPoint, ExtensionRegistry, ProviderEntry
from .runner import HookRunner

CORE = "core"

POINTS = (
    ExtensionPoint(points.DOWNLOADER, "provider", "下载器后端（downloader.type）"),
    ExtensionPoint(
        points.NOTIFIER, "provider", "通知渠道（notification.providers[].type）"
    ),
    ExtensionPoint(points.LLM_PROVIDER, "provider", "LLM 解析提供商（llm.provider）"),
    ExtensionPoint(points.SEARCH_SITE, "provider", "搜索站点"),
    ExtensionPoint(points.SCHEDULED_TASK, "provider", "定时任务"),
    # --- P3 ingest ---
    ExtensionPoint(
        points.METADATA_PROVIDER, "provider", "元数据源（RSS 订阅的 parser）"
    ),
    ExtensionPoint(
        points.TORRENT_FILTER, "filter", "已匹配规则的种子是否下载", fail_open=True
    ),
    ExtensionPoint(points.TITLE_PARSED, "transform", "修正标题解析结果"),
    ExtensionPoint(points.TORRENT_ADDING, "transform", "修改发给下载器的添加请求"),
    ExtensionPoint(points.HTTP_REQUEST, "transform", "修改宿主 GET 请求的请求头"),
)

_registry: ExtensionRegistry | None = None
# 由 AppContext 在构建时设置；未设置时（测试、CLI）钩子一律跳过，只执行宿主逻辑
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


def set_runner(runner: HookRunner | None) -> None:
    global _runner
    _runner = runner


def get_runner() -> HookRunner | None:
    return _runner


def hook_runner(point: str) -> HookRunner | None:
    """返回可执行 ``point`` 钩子的 runner；未设置 runner 或该扩展点没有钩子
    时返回 None，调用方据此走与无插件时完全相同的路径（逐条种子的热路径
    不付出构造快照、调度协程的开销）。"""
    runner = _runner
    if runner is None or not runner.has_hooks(point):
        return None
    return runner


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

    # 元数据源：沿用 RSSItem.parser 的取值（mikan / tmdb），实现延迟 import
    def metadata(name: str):
        def factory():
            from module.rss import metadata as core_metadata

            return core_metadata.CORE_PROVIDERS[name]

        return factory

    for provider_id in ("mikan", "tmdb"):
        registry.add_provider(
            points.METADATA_PROVIDER,
            ProviderEntry(CORE, provider_id, metadata(provider_id)),
        )

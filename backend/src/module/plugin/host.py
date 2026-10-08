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

from ab_sdk import Event, points
from ab_sdk.downloader import DownloaderConnection
from ab_sdk.rename import CORE_ID

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
    # --- P4 organize ---
    ExtensionPoint(
        points.RENAME_STRATEGY, "provider", "重命名方式（bangumi_manage.rename_method）"
    ),
    ExtensionPoint(points.MEDIA_FILES, "provider", "种子内文件分类（正片 / 字幕）"),
    ExtensionPoint(points.CONFLICT_POLICY, "provider", "目标路径被占用时保留或替换"),
)

_registry: ExtensionRegistry | None = None
# 进程级事件总线与钩子执行器，由 AppContext 在构造时设置（即 PluginManager
# 持有的那一份）；未设置时（单元测试、脚本、CLI）发布事件为空操作、钩子一律
# 跳过，只执行宿主逻辑
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

    # organize：重命名方式 none、按扩展名分类、版本冲突策略
    from module.downloader.path import SuffixMediaFiles
    from module.manager.rename_strategies import (
        NO_RENAME,
        AdvanceRename,
        NoRename,
        PnRename,
    )
    from module.manager.revision_policy import CoreConflictPolicy

    _core(registry, points.RENAME_STRATEGY, NO_RENAME, NoRename())
    _core(registry, points.RENAME_STRATEGY, "pn", PnRename())
    _core(registry, points.RENAME_STRATEGY, "advance", AdvanceRename())
    _core(registry, points.MEDIA_FILES, CORE_ID, SuffixMediaFiles())
    _core(registry, points.CONFLICT_POLICY, CORE_ID, CoreConflictPolicy())


# --- P5 events/api ---------------------------------------------------------


def get_bus() -> EventBus | None:
    return _bus


def set_bus(bus: EventBus | None) -> None:
    global _bus
    _bus = bus


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

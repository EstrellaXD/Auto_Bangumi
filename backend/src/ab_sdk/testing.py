"""插件单元测试辅助：不启动 AutoBangumi 也能实例化并驱动插件。

示例::

    from ab_sdk.testing import create_plugin

    async def test_my_filter(tmp_path):
        plugin, ctx = create_plugin(MyPlugin, {"keyword": "1080p"}, data_dir=tmp_path)
        await plugin.setup()
        verdict = await plugin.check(torrent)
        assert verdict.accept
        assert ctx.bus.published == []

Provider 契约测试套件（``DownloaderContract``、``RenameStrategyContract``、
``NotifierContract``、``SearchSiteContract``）：继承它们并实现 ``create()``，
pytest 会收集其中的 ``test_*``::

    from ab_sdk.testing import RenameStrategyContract, create_plugin

    class TestMyStrategy(RenameStrategyContract):
        def create(self):
            plugin, _ = create_plugin(MyPlugin)
            return plugin.strategy()

套件里的用例是同步的（内部用 ``asyncio.run``），不要求安装 pytest-asyncio。
宿主自带的实现与内置插件也用同一套件验证。
"""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Any, ClassVar, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

from .downloader import (
    AddResult,
    CoreDownloaderClient,
    DownloaderCapabilities,
)
from .events import Event
from .notify import NotificationMessage, Notifier
from .plugin import Plugin
from .rename import RenameInput, RenameSkipped, RenameStrategy
from .search import SearchSite

P = TypeVar("P", bound=Plugin[Any])


class MemoryKV:
    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)


class RecordingBus:
    """记录插件发布的事件；``deliver`` 把事件同步投递给插件自己的订阅者。"""

    def __init__(self) -> None:
        self.published: list[Event] = []
        self._handlers: list[tuple[str, Callable[[Event], Awaitable[None] | None]]] = []

    def publish(self, event: Event) -> None:
        self.published.append(event)

    def subscribe(
        self, kind: str, handler: Callable[[Event], Awaitable[None] | None]
    ) -> Callable[[], None]:
        entry = (kind, handler)
        self._handlers.append(entry)
        return lambda: self._handlers.remove(entry)

    async def deliver(self, event: Event) -> None:
        for kind, handler in list(self._handlers):
            if kind in ("*", event.kind):
                result = handler(event)
                if inspect.isawaitable(result):
                    await result


class FakeContext:
    def __init__(
        self,
        plugin_id: str,
        config: BaseModel | None,
        data_dir: Path,
    ) -> None:
        self.plugin_id = plugin_id
        self.config = config
        self.log = logging.getLogger(f"plugin.{plugin_id}")
        self.bus = RecordingBus()
        self.kv = MemoryKV()
        self.data_dir = data_dir


def create_plugin(
    plugin_cls: type[P],
    options: dict[str, Any] | None = None,
    *,
    plugin_id: str = "test-plugin",
    data_dir: Path | None = None,
) -> tuple[P, FakeContext]:
    """按宿主的规则校验配置并构造插件（不调用 setup）。"""
    config = None
    if plugin_cls.config_model is not None:
        config = plugin_cls.config_model.model_validate(options or {})
    ctx = FakeContext(plugin_id, config, data_dir or Path("plugin-data") / plugin_id)
    return plugin_cls(ctx), ctx


# ----------------------------------------------------------------- 契约套件

T = TypeVar("T")


def _run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


class DownloaderContract:
    """下载器客户端契约。

    结构检查总是运行：满足 :class:`CoreDownloaderClient`、声明
    :class:`DownloaderCapabilities`、声明的能力都有对应方法。行为检查需要一个
    可用的后端，子类确认 ``create()`` 返回的客户端连着可用后端（或替身）后设
    ``behavioral = True`` 才会运行。
    """

    behavioral: ClassVar[bool] = False
    # 能力 → 声明该能力就必须实现的方法
    CAPABILITY_METHODS: ClassVar[dict[str, tuple[str, ...]]] = {
        "can_query": ("torrents_info", "torrent_exists", "torrents_files"),
        "can_rename": ("torrents_rename_file",),
        "can_manage": (
            "torrents_delete",
            "torrents_pause",
            "torrents_resume",
            "move_torrent",
            "set_category",
            "add_tag",
        ),
        "can_rss_rules": ("rss_set_rule", "add_category"),
    }
    MAGNET = "magnet:?xt=urn:btih:" + "a" * 40

    def create(self) -> CoreDownloaderClient:
        raise NotImplementedError

    def test_client_implements_core_protocol(self) -> None:
        assert isinstance(self.create(), CoreDownloaderClient)

    def test_capabilities_are_declared(self) -> None:
        caps = self.create().capabilities
        assert isinstance(caps, DownloaderCapabilities)
        assert all(isinstance(v, bool) for v in vars(caps).values())

    def test_declared_capabilities_have_methods(self) -> None:
        client = self.create()
        for capability, methods in self.CAPABILITY_METHODS.items():
            if getattr(client.capabilities, capability):
                for method in methods:
                    assert callable(
                        getattr(client, method, None)
                    ), f"声明了 {capability}，但缺少 {method}"

    def test_auth_succeeds_and_logout_is_safe(self) -> None:
        if not self.behavioral:
            return
        client = self.create()

        async def scenario() -> None:
            assert await client.auth() is True
            await client.logout()
            await client.logout()  # 重复登出不得抛错

        _run(scenario())

    def test_add_torrents_returns_accepted_result(self) -> None:
        if not self.behavioral:
            return
        client = self.create()

        async def scenario() -> AddResult:
            await client.auth()
            return await client.add_torrents(
                [self.MAGNET], None, "/downloads/Bangumi/Contract", "Bangumi", "ab:0"
            )

        assert _run(scenario()) in (AddResult.ADDED, AddResult.DUPLICATE)

    def test_query_unknown_torrent_is_not_found(self) -> None:
        if not self.behavioral:
            return
        client: Any = self.create()
        if not client.capabilities.can_query:
            return

        async def scenario() -> None:
            await client.auth()
            assert isinstance(await client.torrents_info(None, "Bangumi"), list)
            assert not await client.torrent_exists("0" * 40)
            assert await client.torrents_files("0" * 40) == []

        _run(scenario())


class RenameStrategyContract:
    """重命名方式契约：返回种子内的新相对路径，或抛出 :class:`RenameSkipped`。"""

    def create(self) -> RenameStrategy:
        raise NotImplementedError

    def samples(self) -> list[RenameInput]:
        """用于检查的输入；策略只适用于特定输入时覆盖它。"""
        media = RenameInput(
            kind="media",
            media_path="[Group] Sample - 05 [1080p].mkv",
            title="Sample",
            bangumi_name="Sample (2024)",
            season=1,
            episode=5,
            suffix=".mkv",
            group="Group",
        )
        return [
            media,
            replace(
                media,
                media_path="[Group] Sample - 09.5 [1080p].mp4",
                episode=9.5,
                suffix=".mp4",
                episode_type="special",
            ),
            replace(
                media,
                media_path="Sample Movie.mkv",
                episode=1,
                episode_type="movie",
            ),
            replace(
                media,
                kind="subtitle",
                media_path="[Group] Sample - 05.zh.ass",
                suffix=".ass",
                language="zh",
            ),
        ]

    def _names(self) -> list[tuple[RenameInput, str]]:
        strategy = self.create()
        names = []
        for f in self.samples():
            try:
                names.append((f, strategy.target_name(f)))
            except RenameSkipped:
                continue  # 明确放弃该文件是契约允许的结果
        return names

    def test_target_name_is_relative_path_inside_torrent(self) -> None:
        for _, name in self._names():
            assert isinstance(name, str) and name
            path = PurePosixPath(name)
            assert not path.is_absolute()
            assert ".." not in path.parts

    def test_target_name_keeps_file_suffix(self) -> None:
        for f, name in self._names():
            assert name.endswith(f.suffix), f"{name!r} 丢失了扩展名 {f.suffix}"

    def test_target_name_is_deterministic(self) -> None:
        assert self._names() == self._names()


class NotifierContract:
    """通知渠道契约。``create()`` 返回后端接受消息的渠道；能构造出后端拒绝消息
    的渠道时覆盖 ``create_failing()``，会额外检查失败以返回值而非异常表达。"""

    def create(self) -> Notifier:
        raise NotImplementedError

    def create_failing(self) -> Notifier | None:
        return None

    @staticmethod
    def episode_message() -> NotificationMessage:
        return NotificationMessage(
            kind="episode",
            title="Sample",
            body="Sample S01E05",
            official_title="Sample",
            season=1,
            episode=5,
        )

    @staticmethod
    def event_message() -> NotificationMessage:
        return NotificationMessage(kind="event", title="RSS 失败", body="详情")

    def test_send_episode_message_returns_true(self) -> None:
        notifier = self.create()
        assert _run(notifier.send(self.episode_message())) is True

    def test_send_event_message_returns_true(self) -> None:
        notifier = self.create()
        assert _run(notifier.send(self.event_message())) is True

    def test_test_returns_success_and_message(self) -> None:
        ok, message = _run(self.create().test())
        assert ok is True
        assert isinstance(message, str)

    def test_rejected_message_returns_false_without_raising(self) -> None:
        notifier = self.create_failing()
        if notifier is None:
            return
        assert _run(notifier.send(self.episode_message())) is False
        ok, message = _run(notifier.test())
        assert ok is False
        assert isinstance(message, str)


class SearchSiteContract:
    """搜索站点契约：URL 模板含 ``%s``，解析器为 ``mikan`` 或 ``tmdb``。"""

    def create(self) -> SearchSite:
        raise NotImplementedError

    def test_site_is_search_site(self) -> None:
        assert isinstance(self.create(), SearchSite)

    def test_url_template_has_one_keyword_placeholder(self) -> None:
        url = self.create().url
        assert url.count("%s") == 1
        parsed = urlparse(url.replace("%s", "keyword"))
        assert parsed.scheme in ("http", "https") and parsed.netloc

    def test_parser_is_known_metadata_source(self) -> None:
        assert self.create().parser in ("mikan", "tmdb")

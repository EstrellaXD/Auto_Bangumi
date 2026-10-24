"""宿主自带的 Provider 与内置插件通过 ``ab_sdk.testing`` 的契约套件。"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from ab_sdk import points
from ab_sdk.downloader import DownloaderConnection
from ab_sdk.notify import NotificationMessage
from ab_sdk.search import SearchSite
from ab_sdk.testing import (
    DownloaderContract,
    NotifierContract,
    RenameStrategyContract,
    SearchSiteContract,
)
from module.conf.search_provider import DEFAULT_PROVIDER
from module.models.bangumi import Notification
from module.models.config import NotificationProvider as ProviderConfig
from module.notification.base import NotificationProvider
from module.plugin.host import provider as host_provider

# ------------------------------------------------------------------ 下载器

_CONNECTION = DownloaderConnection("localhost:8080", "admin", "secret", False)


def _registered(point: str, provider_id: str) -> Any:
    impl = host_provider(point, provider_id)
    assert impl is not None, f"{point} {provider_id} 未登记"
    return impl


def _downloader(provider_id: str):
    return _registered(points.DOWNLOADER, provider_id)(_CONNECTION)


class TestMockDownloaderContract(DownloaderContract):
    behavioral = True

    def create(self):
        return _downloader("mock")


class TestQbittorrentContract(DownloaderContract):
    def create(self):
        return _downloader("qbittorrent")


class TestAria2Contract(DownloaderContract):
    def create(self):
        return _downloader("aria2")


# ------------------------------------------------------------------ 重命名


def _strategy(provider_id: str):
    return _registered(points.RENAME_STRATEGY, provider_id)


class TestNoRenameContract(RenameStrategyContract):
    def create(self):
        return _strategy("none")


class TestPnContract(RenameStrategyContract):
    def create(self):
        return _strategy("pn")


class TestAdvanceContract(RenameStrategyContract):
    def create(self):
        return _strategy("advance")


class TestTemplateContract(RenameStrategyContract):
    def create(self):
        return _strategy("template")


# ------------------------------------------------------------------ 通知


class _CoreNotifier:
    """把宿主的渠道（接收 ``Notification`` 与整条配置）适配为 SDK 的 Notifier。

    HTTP 层换成固定状态码的替身，契约套件因此能在没有网络的环境里运行。
    """

    def __init__(self, config: ProviderConfig, status_code: int) -> None:
        self._provider: NotificationProvider = _registered(
            points.NOTIFIER, config.type
        )(config)
        response = SimpleNamespace(status_code=status_code, json=lambda: {})
        for name in ("post_data", "post_files", "_post_json"):
            setattr(self._provider, name, AsyncMock(return_value=response))

    async def send(self, message: NotificationMessage) -> bool:
        if message.kind == "event":
            return await self._provider._deliver_text(message.title, message.body)
        assert message.official_title is not None
        return await self._provider.send(
            Notification(
                official_title=message.official_title,
                season=message.season or 1,
                episode=message.episode or 1,
                poster_path="",
            )
        )

    async def test(self) -> tuple[bool, str]:
        return await self._provider.test()


def _core_notifier_suite(**config: str) -> type[NotifierContract]:
    provider_config = ProviderConfig.model_validate(config)

    class Suite(NotifierContract):
        def create(self):
            return _CoreNotifier(provider_config, 200)

        def create_failing(self):
            return _CoreNotifier(provider_config, 500)

    return Suite


TestTelegramContract = _core_notifier_suite(type="telegram", token="t", chat_id="1")
TestDiscordContract = _core_notifier_suite(
    type="discord", webhook_url="https://discord.example/hook"
)
TestBarkContract = _core_notifier_suite(type="bark", device_key="device")
TestServerChanContract = _core_notifier_suite(type="server-chan", token="t")
TestWecomContract = _core_notifier_suite(
    type="wecom", webhook_url="https://wecom.example/hook", token="t"
)
TestGotifyContract = _core_notifier_suite(
    type="gotify", server_url="https://gotify.example", token="t"
)
TestPushoverContract = _core_notifier_suite(
    type="pushover", user_key="u", api_token="t"
)
TestWebhookContract = _core_notifier_suite(
    type="webhook", url="https://hook.example/ab"
)


# ------------------------------------------------------------------ 搜索站点


def _default_site_suite(site_id: str) -> type[SearchSiteContract]:
    class Suite(SearchSiteContract):
        def create(self):
            return SearchSite(**DEFAULT_PROVIDER[site_id])

    return Suite


TestMikanSiteContract = _default_site_suite("mikan")
TestAnibtSiteContract = _default_site_suite("anibt")
TestNyaaSiteContract = _default_site_suite("nyaa")
TestDmhySiteContract = _default_site_suite("dmhy")

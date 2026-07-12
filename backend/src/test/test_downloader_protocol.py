"""Conformance tests for the download-client protocol and capabilities.

QbDownloader and MockDownloader implement the full async surface; Aria2Downloader
implements query/rename/manage for real but has no qB-native RSS-rule/prefs
surface (can_rss_rules=False). All three advertise their capabilities.
"""

from module.downloader.base import (
    CoreDownloaderClient,
    DownloaderCapabilities,
    DownloaderClient,
    RenameOutcome,
    RenameResult,
)
from module.downloader.client.aria2_downloader import Aria2Downloader
from module.downloader.client.mock_downloader import MockDownloader
from module.downloader.client.qb_downloader import QbDownloader


def _qb() -> QbDownloader:
    return QbDownloader("localhost:8080", "u", "p", False)


def _aria2() -> Aria2Downloader:
    return Aria2Downloader("http://localhost:6800", "u", "p")


def _mock() -> MockDownloader:
    return MockDownloader()


class TestCapabilities:
    def test_qb_supports_everything(self):
        assert QbDownloader.capabilities == DownloaderCapabilities(
            can_query=True, can_rename=True, can_manage=True, can_rss_rules=True
        )

    def test_mock_supports_everything(self):
        assert MockDownloader.capabilities == DownloaderCapabilities(
            can_query=True, can_rename=True, can_manage=True, can_rss_rules=True
        )

    def test_aria2_supports_query_rename_manage_but_not_rss_rules(self):
        assert Aria2Downloader.capabilities == DownloaderCapabilities(
            can_query=True, can_rename=True, can_manage=True, can_rss_rules=False
        )

    def test_all_three_expose_capabilities(self):
        for cls in (QbDownloader, MockDownloader, Aria2Downloader):
            assert isinstance(cls.capabilities, DownloaderCapabilities)


class TestRenameResult:
    def test_success_outcomes_preserve_boolean_compatibility(self):
        assert RenameResult(RenameOutcome.RENAMED)
        assert RenameResult(RenameOutcome.ALREADY_APPLIED)

    def test_failure_outcomes_are_false(self):
        assert not RenameResult(RenameOutcome.DESTINATION_EXISTS)
        assert not RenameResult(RenameOutcome.RETRYABLE_FAILURE)


class TestProtocolConformance:
    def test_qb_satisfies_full_protocol(self):
        assert isinstance(_qb(), DownloaderClient)

    def test_mock_satisfies_full_protocol(self):
        assert isinstance(_mock(), DownloaderClient)

    def test_aria2_does_not_satisfy_full_protocol(self):
        assert not isinstance(_aria2(), DownloaderClient)

    def test_aria2_satisfies_core_protocol(self):
        assert isinstance(_aria2(), CoreDownloaderClient)

    def test_qb_and_mock_satisfy_core_protocol(self):
        assert isinstance(_qb(), CoreDownloaderClient)
        assert isinstance(_mock(), CoreDownloaderClient)

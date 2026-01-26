"""Tests for DownloadClient: init, set_rule, add_torrent, rename, etc."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from module.models import Bangumi, Torrent
from module.models.config import Config
from module.downloader.download_client import DownloadClient

from test.factories import make_bangumi, make_torrent


@pytest.fixture
def download_client(mock_qb_client):
    """Create a DownloadClient with mocked internal client."""
    with patch("module.downloader.download_client.settings") as mock_settings:
        mock_settings.downloader.type = "qbittorrent"
        mock_settings.downloader.host = "localhost:8080"
        mock_settings.downloader.username = "admin"
        mock_settings.downloader.password = "admin"
        mock_settings.downloader.ssl = False
        mock_settings.downloader.path = "/downloads/Bangumi"
        mock_settings.bangumi_manage.group_tag = False
        with patch(
            "module.downloader.download_client.DownloadClient._DownloadClient__getClient",
            return_value=mock_qb_client,
        ):
            client = DownloadClient()
    client.client = mock_qb_client
    return client


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


class TestAuth:
    async def test_auth_success(self, download_client, mock_qb_client):
        """auth() sets authed=True when client authenticates."""
        mock_qb_client.auth.return_value = True
        await download_client.auth()
        assert download_client.authed is True

    async def test_auth_failure(self, download_client, mock_qb_client):
        """auth() keeps authed=False when client fails."""
        mock_qb_client.auth.return_value = False
        await download_client.auth()
        assert download_client.authed is False


# ---------------------------------------------------------------------------
# init_downloader
# ---------------------------------------------------------------------------


class TestInitDownloader:
    async def test_sets_prefs_and_category(self, download_client, mock_qb_client):
        """init_downloader calls prefs_init with RSS config and adds category."""
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            await download_client.init_downloader()

        mock_qb_client.prefs_init.assert_called_once()
        prefs_arg = mock_qb_client.prefs_init.call_args[1]["prefs"]
        assert prefs_arg["rss_auto_downloading_enabled"] is True
        assert prefs_arg["rss_refresh_interval"] == 30
        mock_qb_client.add_category.assert_called_once_with("BangumiCollection")

    async def test_detects_path_when_empty(self, download_client, mock_qb_client):
        """When downloader.path is empty, fetches from app prefs."""
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.path = ""
            mock_qb_client.get_app_prefs.return_value = {"save_path": "/data"}
            await download_client.init_downloader()

        assert mock_settings.downloader.path != ""
        assert "Bangumi" in mock_settings.downloader.path

    async def test_category_already_exists_no_error(self, download_client, mock_qb_client):
        """If category already exists, logs debug but doesn't crash."""
        mock_qb_client.add_category.side_effect = Exception("already exists")
        with patch("module.downloader.download_client.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            # Should not raise
            await download_client.init_downloader()


# ---------------------------------------------------------------------------
# set_rule
# ---------------------------------------------------------------------------


class TestSetRule:
    async def test_generates_correct_rule(self, download_client, mock_qb_client):
        """set_rule creates a rule with correct mustContain and savePath."""
        bangumi = make_bangumi(
            title_raw="Mushoku Tensei",
            filter="720,480",
            official_title="Mushoku Tensei",
            season=2,
            year="2024",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            await download_client.set_rule(bangumi)

        mock_qb_client.rss_set_rule.assert_called_once()
        call_kwargs = mock_qb_client.rss_set_rule.call_args[1]
        rule = call_kwargs["rule_def"]
        assert rule["mustContain"] == "Mushoku Tensei"
        # filter string is joined char-by-char with "|" (this is how the code works)
        assert rule["mustNotContain"] == "|".join("720,480")
        assert rule["enable"] is True
        assert "Season 2" in rule["savePath"]

    async def test_marks_bangumi_added(self, download_client, mock_qb_client):
        """set_rule sets data.added=True after creating the rule."""
        bangumi = make_bangumi(added=False, filter="")
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            await download_client.set_rule(bangumi)

        assert bangumi.added is True

    async def test_rule_name_set(self, download_client, mock_qb_client):
        """set_rule populates rule_name and save_path on the Bangumi."""
        bangumi = make_bangumi(
            official_title="My Anime",
            season=1,
            filter="",
            rule_name=None,
            save_path=None,
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = False
            await download_client.set_rule(bangumi)

        assert bangumi.rule_name is not None
        assert "My Anime" in bangumi.rule_name
        assert bangumi.save_path is not None

    async def test_rule_name_with_group_tag(self, download_client, mock_qb_client):
        """When group_tag=True, rule_name includes [group]."""
        bangumi = make_bangumi(
            official_title="My Anime",
            group_name="SubGroup",
            season=1,
            filter="",
        )
        with patch("module.downloader.path.settings") as mock_settings:
            mock_settings.downloader.path = "/downloads/Bangumi"
            mock_settings.bangumi_manage.group_tag = True
            await download_client.set_rule(bangumi)

        assert "[SubGroup]" in bangumi.rule_name


# ---------------------------------------------------------------------------
# add_torrent
# ---------------------------------------------------------------------------


class TestAddTorrent:
    async def test_magnet_url(self, download_client, mock_qb_client):
        """Magnet URLs are passed as torrent_urls, no file download."""
        torrent = make_torrent(url="magnet:?xt=urn:btih:abc123")
        bangumi = make_bangumi()

        with patch("module.downloader.download_client.RequestContent") as MockReq:
            mock_req = AsyncMock()
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await download_client.add_torrent(torrent, bangumi)

        assert result is True
        call_kwargs = mock_qb_client.add_torrents.call_args[1]
        assert call_kwargs["torrent_urls"] == "magnet:?xt=urn:btih:abc123"
        assert call_kwargs["torrent_files"] is None

    async def test_file_url_downloads_content(self, download_client, mock_qb_client):
        """Non-magnet URLs trigger file download and pass as torrent_files."""
        torrent = make_torrent(url="https://example.com/file.torrent")
        bangumi = make_bangumi()

        with patch("module.downloader.download_client.RequestContent") as MockReq:
            mock_req = AsyncMock()
            mock_req.get_content = AsyncMock(return_value=b"torrent-file-data")
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await download_client.add_torrent(torrent, bangumi)

        assert result is True
        call_kwargs = mock_qb_client.add_torrents.call_args[1]
        assert call_kwargs["torrent_files"] == b"torrent-file-data"
        assert call_kwargs["torrent_urls"] is None

    async def test_list_magnet_urls(self, download_client, mock_qb_client):
        """List of magnet torrents are joined as list of URLs."""
        torrents = [
            make_torrent(url="magnet:?xt=urn:btih:aaa"),
            make_torrent(url="magnet:?xt=urn:btih:bbb"),
            make_torrent(url="magnet:?xt=urn:btih:ccc"),
        ]
        bangumi = make_bangumi()

        with patch("module.downloader.download_client.RequestContent") as MockReq:
            mock_req = AsyncMock()
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await download_client.add_torrent(torrents, bangumi)

        assert result is True
        call_kwargs = mock_qb_client.add_torrents.call_args[1]
        assert len(call_kwargs["torrent_urls"]) == 3

    async def test_empty_list_returns_false(self, download_client, mock_qb_client):
        """Empty torrent list returns False without calling client."""
        bangumi = make_bangumi()
        with patch("module.downloader.download_client.RequestContent") as MockReq:
            mock_req = AsyncMock()
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await download_client.add_torrent([], bangumi)

        assert result is False
        mock_qb_client.add_torrents.assert_not_called()

    async def test_client_rejects_returns_false(self, download_client, mock_qb_client):
        """When client.add_torrents returns False, returns False."""
        mock_qb_client.add_torrents.return_value = False
        torrent = make_torrent(url="magnet:?xt=urn:btih:abc")
        bangumi = make_bangumi()

        with patch("module.downloader.download_client.RequestContent") as MockReq:
            mock_req = AsyncMock()
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await download_client.add_torrent(torrent, bangumi)

        assert result is False

    async def test_generates_save_path_if_missing(self, download_client, mock_qb_client):
        """When bangumi.save_path is empty, generates one."""
        torrent = make_torrent(url="magnet:?xt=urn:btih:abc")
        bangumi = make_bangumi(save_path=None)

        with patch("module.downloader.download_client.RequestContent") as MockReq:
            mock_req = AsyncMock()
            MockReq.return_value.__aenter__ = AsyncMock(return_value=mock_req)
            MockReq.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch("module.downloader.path.settings") as mock_settings:
                mock_settings.downloader.path = "/downloads/Bangumi"
                await download_client.add_torrent(torrent, bangumi)

        assert bangumi.save_path is not None


# ---------------------------------------------------------------------------
# get_torrent_info / rename_torrent_file / delete_torrent
# ---------------------------------------------------------------------------


class TestClientDelegation:
    async def test_get_torrent_info(self, download_client, mock_qb_client):
        """get_torrent_info delegates to client.torrents_info."""
        mock_qb_client.torrents_info.return_value = [
            {"hash": "abc", "name": "test", "save_path": "/test"}
        ]
        result = await download_client.get_torrent_info()
        mock_qb_client.torrents_info.assert_called_once_with(
            status_filter="completed", category="Bangumi", tag=None
        )
        assert len(result) == 1

    async def test_rename_torrent_file_success(self, download_client, mock_qb_client):
        """rename_torrent_file returns True on success."""
        mock_qb_client.torrents_rename_file.return_value = True
        result = await download_client.rename_torrent_file("hash1", "old.mkv", "new.mkv")
        assert result is True

    async def test_rename_torrent_file_failure(self, download_client, mock_qb_client):
        """rename_torrent_file returns False on failure."""
        mock_qb_client.torrents_rename_file.return_value = False
        result = await download_client.rename_torrent_file("hash1", "old.mkv", "new.mkv")
        assert result is False

    async def test_delete_torrent(self, download_client, mock_qb_client):
        """delete_torrent delegates to client.torrents_delete."""
        await download_client.delete_torrent("hash1", delete_files=True)
        mock_qb_client.torrents_delete.assert_called_once_with("hash1", delete_files=True)

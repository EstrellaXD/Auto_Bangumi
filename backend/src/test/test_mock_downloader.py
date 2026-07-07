"""Tests for MockDownloader - state management and API contract."""

import pytest

from module.downloader import AddResult
from module.downloader.client.mock_downloader import MockDownloader


@pytest.fixture
def mock_dl() -> MockDownloader:
    """Fresh MockDownloader for each test."""
    return MockDownloader()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestMockDownloaderInit:
    def test_initial_state_is_empty(self, mock_dl):
        """MockDownloader starts with no torrents, rules, or feeds."""
        state = mock_dl.get_state()
        assert state["torrents"] == {}
        assert state["rules"] == {}
        assert state["feeds"] == {}

    def test_initial_categories(self, mock_dl):
        """Default categories include Bangumi and BangumiCollection."""
        state = mock_dl.get_state()
        assert "Bangumi" in state["categories"]
        assert "BangumiCollection" in state["categories"]

    def test_initial_prefs(self, mock_dl):
        """Default prefs are populated."""
        # Access private attribute directly to confirm defaults
        assert mock_dl._prefs["rss_auto_downloading_enabled"] is True
        assert mock_dl._prefs["rss_max_articles_per_feed"] == 500


# ---------------------------------------------------------------------------
# Auth / connection
# ---------------------------------------------------------------------------


class TestMockDownloaderAuth:
    async def test_auth_returns_true(self, mock_dl):
        result = await mock_dl.auth()
        assert result is True

    async def test_auth_retry_param_accepted(self, mock_dl):
        result = await mock_dl.auth(retry=5)
        assert result is True

    async def test_logout_does_not_raise(self, mock_dl):
        await mock_dl.logout()

    async def test_check_host_returns_true(self, mock_dl):
        result = await mock_dl.check_host()
        assert result is True

    async def test_check_connection_returns_version_string(self, mock_dl):
        result = await mock_dl.check_connection()
        assert "mock" in result.lower()


# ---------------------------------------------------------------------------
# Prefs
# ---------------------------------------------------------------------------


class TestMockDownloaderPrefs:
    async def test_prefs_init_updates_prefs(self, mock_dl):
        """prefs_init merges given prefs into the internal store."""
        await mock_dl.prefs_init({"rss_refresh_interval": 60, "custom_key": "val"})
        assert mock_dl._prefs["rss_refresh_interval"] == 60
        assert mock_dl._prefs["custom_key"] == "val"

    async def test_get_app_prefs_returns_dict(self, mock_dl):
        result = await mock_dl.get_app_prefs()
        assert isinstance(result, dict)
        assert "save_path" in result


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class TestMockDownloaderCategories:
    async def test_add_category_persists(self, mock_dl):
        await mock_dl.add_category("NewCategory")
        state = mock_dl.get_state()
        assert "NewCategory" in state["categories"]

    async def test_add_duplicate_category_no_error(self, mock_dl):
        await mock_dl.add_category("Bangumi")
        state = mock_dl.get_state()
        # Still only one entry for Bangumi (set semantics)
        assert state["categories"].count("Bangumi") == 1


# ---------------------------------------------------------------------------
# Torrent management
# ---------------------------------------------------------------------------


class TestMockDownloaderAddTorrents:
    async def test_add_torrent_url_returns_true(self, mock_dl):
        result = await mock_dl.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:abc",
            torrent_files=None,
            save_path="/downloads/Bangumi",
            category="Bangumi",
        )
        assert result is AddResult.ADDED

    async def test_add_torrent_stores_in_state(self, mock_dl):
        await mock_dl.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:abc",
            torrent_files=None,
            save_path="/downloads/Bangumi",
            category="Bangumi",
        )
        state = mock_dl.get_state()
        assert len(state["torrents"]) == 1

    async def test_add_torrent_with_tag_stored(self, mock_dl):
        await mock_dl.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:abc",
            torrent_files=None,
            save_path="/downloads/Bangumi",
            category="Bangumi",
            tags="ab:42",
        )
        state = mock_dl.get_state()
        torrent = list(state["torrents"].values())[0]
        assert torrent["tags"] == "ab:42"

    async def test_add_torrent_with_file_bytes(self, mock_dl):
        result = await mock_dl.add_torrents(
            torrent_urls=None,
            torrent_files=b"\x00\x01\x02",
            save_path="/downloads",
            category="Bangumi",
        )
        assert result is AddResult.ADDED

    async def test_two_different_torrents_stored_separately(self, mock_dl):
        await mock_dl.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:aaa",
            torrent_files=None,
            save_path="/dl",
            category="Bangumi",
        )
        await mock_dl.add_torrents(
            torrent_urls="magnet:?xt=urn:btih:bbb",
            torrent_files=None,
            save_path="/dl",
            category="Bangumi",
        )
        state = mock_dl.get_state()
        assert len(state["torrents"]) == 2


class TestMockDownloaderTorrentsInfo:
    async def test_returns_all_when_no_filter(self, mock_dl):
        mock_dl.add_mock_torrent("Anime A", category="Bangumi")
        mock_dl.add_mock_torrent("Anime B", category="Bangumi")
        result = await mock_dl.torrents_info(status_filter=None, category=None)
        assert len(result) == 2

    async def test_filters_by_category(self, mock_dl):
        mock_dl.add_mock_torrent("Anime A", category="Bangumi")
        mock_dl.add_mock_torrent("Movie", category="BangumiCollection")
        result = await mock_dl.torrents_info(status_filter=None, category="Bangumi")
        assert len(result) == 1
        assert result[0]["name"] == "Anime A"

    async def test_filters_by_tag(self, mock_dl):
        h1 = mock_dl.add_mock_torrent("Anime A", category="Bangumi")
        mock_dl.add_mock_torrent("Anime B", category="Bangumi")
        # Manually set the tag on first torrent
        mock_dl._torrents[h1]["tags"] = ["ab:1"]
        result = await mock_dl.torrents_info(
            status_filter=None, category=None, tag="ab:1"
        )
        assert len(result) == 1
        assert result[0]["name"] == "Anime A"

    async def test_empty_store_returns_empty_list(self, mock_dl):
        result = await mock_dl.torrents_info(status_filter=None, category="Bangumi")
        assert result == []


class TestMockDownloaderTorrentsFiles:
    async def test_returns_files_for_known_hash(self, mock_dl):
        files = [{"name": "ep01.mkv", "size": 500_000_000}]
        h = mock_dl.add_mock_torrent("Anime", files=files)
        result = await mock_dl.torrents_files(torrent_hash=h)
        assert len(result) == 1
        assert result[0]["name"] == "ep01.mkv"

    async def test_returns_empty_list_for_unknown_hash(self, mock_dl):
        result = await mock_dl.torrents_files(torrent_hash="nonexistent")
        assert result == []


class TestMockDownloaderDelete:
    async def test_delete_single_torrent(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime")
        await mock_dl.torrents_delete(hash=h)
        assert h not in mock_dl._torrents

    async def test_delete_multiple_torrents_pipe_separated(self, mock_dl):
        h1 = mock_dl.add_mock_torrent("Anime A")
        h2 = mock_dl.add_mock_torrent("Anime B")
        await mock_dl.torrents_delete(hash=f"{h1}|{h2}")
        assert h1 not in mock_dl._torrents
        assert h2 not in mock_dl._torrents

    async def test_delete_nonexistent_hash_no_error(self, mock_dl):
        await mock_dl.torrents_delete(hash="deadbeef")


class TestMockDownloaderPauseResume:
    async def test_pause_sets_state(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime", state="downloading")
        await mock_dl.torrents_pause(hashes=h)
        assert mock_dl._torrents[h]["state"] == "paused"

    async def test_resume_sets_state(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime", state="paused")
        await mock_dl.torrents_resume(hashes=h)
        assert mock_dl._torrents[h]["state"] == "downloading"

    async def test_pause_multiple_pipe_separated(self, mock_dl):
        h1 = mock_dl.add_mock_torrent("Anime A", state="downloading")
        h2 = mock_dl.add_mock_torrent("Anime B", state="downloading")
        await mock_dl.torrents_pause(hashes=f"{h1}|{h2}")
        assert mock_dl._torrents[h1]["state"] == "paused"
        assert mock_dl._torrents[h2]["state"] == "paused"

    async def test_pause_unknown_hash_no_error(self, mock_dl):
        await mock_dl.torrents_pause(hashes="deadbeef")


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------


class TestMockDownloaderRename:
    async def test_rename_returns_true(self, mock_dl):
        result = await mock_dl.torrents_rename_file(
            torrent_hash="hash1",
            old_path="old.mkv",
            new_path="new.mkv",
        )
        assert result is True

    async def test_rename_with_verify_flag(self, mock_dl):
        result = await mock_dl.torrents_rename_file(
            torrent_hash="hash1",
            old_path="old.mkv",
            new_path="new.mkv",
            verify=False,
        )
        assert result is True


# ---------------------------------------------------------------------------
# RSS feed management
# ---------------------------------------------------------------------------


class TestMockDownloaderRssFeeds:
    async def test_add_feed_stored(self, mock_dl):
        await mock_dl.rss_add_feed(url="https://mikan.me/RSS/test", item_path="Mikan")
        feeds = await mock_dl.rss_get_feeds()
        assert "Mikan" in feeds
        assert feeds["Mikan"]["url"] == "https://mikan.me/RSS/test"

    async def test_remove_feed(self, mock_dl):
        await mock_dl.rss_add_feed(url="https://example.com", item_path="Feed1")
        await mock_dl.rss_remove_item(item_path="Feed1")
        feeds = await mock_dl.rss_get_feeds()
        assert "Feed1" not in feeds

    async def test_remove_nonexistent_feed_no_error(self, mock_dl):
        await mock_dl.rss_remove_item(item_path="nonexistent")

    async def test_get_feeds_initially_empty(self, mock_dl):
        feeds = await mock_dl.rss_get_feeds()
        assert feeds == {}


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


class TestMockDownloaderRules:
    async def test_set_rule_stored(self, mock_dl):
        rule_def = {"enable": True, "mustContain": "Anime"}
        await mock_dl.rss_set_rule("rule1", rule_def)
        rules = await mock_dl.get_download_rule()
        assert "rule1" in rules
        assert rules["rule1"]["mustContain"] == "Anime"

    async def test_remove_rule(self, mock_dl):
        await mock_dl.rss_set_rule("rule1", {"enable": True})
        await mock_dl.remove_rule("rule1")
        rules = await mock_dl.get_download_rule()
        assert "rule1" not in rules

    async def test_remove_nonexistent_rule_no_error(self, mock_dl):
        await mock_dl.remove_rule("nonexistent")

    async def test_get_download_rule_initially_empty(self, mock_dl):
        rules = await mock_dl.get_download_rule()
        assert rules == {}


# ---------------------------------------------------------------------------
# Move / path
# ---------------------------------------------------------------------------


class TestMockDownloaderMovePath:
    async def test_move_torrent_updates_save_path(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime", save_path="/old/path")
        await mock_dl.move_torrent(hashes=h, new_location="/new/path")
        assert mock_dl._torrents[h]["save_path"] == "/new/path"

    async def test_move_multiple_pipe_separated(self, mock_dl):
        h1 = mock_dl.add_mock_torrent("Anime A", save_path="/old")
        h2 = mock_dl.add_mock_torrent("Anime B", save_path="/old")
        await mock_dl.move_torrent(hashes=f"{h1}|{h2}", new_location="/new")
        assert mock_dl._torrents[h1]["save_path"] == "/new"
        assert mock_dl._torrents[h2]["save_path"] == "/new"

    async def test_get_torrent_path_known_hash(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime", save_path="/downloads/Bangumi")
        path = await mock_dl.get_torrent_path(h)
        assert path == "/downloads/Bangumi"

    async def test_get_torrent_path_unknown_hash_returns_default(self, mock_dl):
        path = await mock_dl.get_torrent_path("nonexistent")
        assert path == "/tmp/mock-downloads"


# ---------------------------------------------------------------------------
# Category assignment
# ---------------------------------------------------------------------------


class TestMockDownloaderSetCategory:
    async def test_set_category_updates_torrent(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime", category="Bangumi")
        await mock_dl.set_category(h, "BangumiCollection")
        assert mock_dl._torrents[h]["category"] == "BangumiCollection"

    async def test_set_category_unknown_hash_no_error(self, mock_dl):
        await mock_dl.set_category("deadbeef", "Bangumi")


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


class TestMockDownloaderTags:
    async def test_add_tag_appends(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime")
        await mock_dl.add_tag(h, "ab:1")
        assert "ab:1" in mock_dl._torrents[h]["tags"]

    async def test_add_tag_no_duplicates(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime")
        await mock_dl.add_tag(h, "ab:1")
        await mock_dl.add_tag(h, "ab:1")
        assert mock_dl._torrents[h]["tags"].count("ab:1") == 1

    async def test_add_tag_unknown_hash_no_error(self, mock_dl):
        await mock_dl.add_tag("deadbeef", "ab:1")

    async def test_multiple_tags_on_same_torrent(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime")
        await mock_dl.add_tag(h, "ab:1")
        await mock_dl.add_tag(h, "group:sub")
        assert "ab:1" in mock_dl._torrents[h]["tags"]
        assert "group:sub" in mock_dl._torrents[h]["tags"]


# ---------------------------------------------------------------------------
# add_mock_torrent helper
# ---------------------------------------------------------------------------


class TestAddMockTorrentHelper:
    def test_generates_hash_from_name(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime")
        assert h is not None
        assert len(h) == 40  # SHA1 hex digest

    def test_explicit_hash_used(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime", hash="cafebabe" + "0" * 32)
        assert h == "cafebabe" + "0" * 32

    def test_torrent_state_is_completed_by_default(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime")
        assert mock_dl._torrents[h]["state"] == "completed"
        assert mock_dl._torrents[h]["progress"] == 1.0

    def test_torrent_state_custom(self, mock_dl):
        h = mock_dl.add_mock_torrent("Anime", state="downloading")
        assert mock_dl._torrents[h]["state"] == "downloading"
        assert mock_dl._torrents[h]["progress"] == 0.5

    def test_default_file_is_mkv(self, mock_dl):
        h = mock_dl.add_mock_torrent("My Anime")
        files = mock_dl._torrents[h]["files"]
        assert len(files) == 1
        assert files[0]["name"].endswith(".mkv")

    def test_custom_files_stored(self, mock_dl):
        custom_files = [{"name": "ep01.mkv"}, {"name": "ep02.mkv"}]
        h = mock_dl.add_mock_torrent("Anime", files=custom_files)
        assert len(mock_dl._torrents[h]["files"]) == 2

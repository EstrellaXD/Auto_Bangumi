"""Tests for module.mcp.tools - _bangumi_to_dict helper and _dispatch routing."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.mcp.tools import (
    TOOLS,
    _bangumi_to_dict,
    _dispatch,
    handle_tool,
)
from module.models import Bangumi, ResponseModel
from test.factories import make_bangumi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status: bool = True, msg: str = "OK") -> ResponseModel:
    return ResponseModel(status=status, status_code=200, msg_en=msg, msg_zh=msg)


def _mock_db(bangumi_list=None, feeds=None, single=None):
    """Build an async-context-manager mock standing in for ``Database()``.

    The MCP handlers open ``async with Database() as db`` and read repos off
    ``db`` directly, so tests configure the repo AsyncMocks here.
    """
    db = MagicMock()
    if bangumi_list is not None:
        db.bangumi.search_all = AsyncMock(return_value=bangumi_list)
    if feeds is not None:
        db.rss.search_all = AsyncMock(return_value=feeds)
    if single is not None:
        db.bangumi.search_id = AsyncMock(return_value=single)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _mock_sync_manager(bangumi_list=None, single=None):
    """Return a MagicMock standing in for a TorrentManager service.

    Used by handlers that call domain methods (search_all_bangumi, search_one,
    update_rule, delete_rule, disable_rule) rather than reaching repos off db.
    """
    mock_mgr = MagicMock()
    mock_mgr.bangumi.search_all = AsyncMock(return_value=bangumi_list or [])
    mock_mgr.search_all_bangumi = AsyncMock(return_value=bangumi_list or [])
    mock_mgr.search_one = AsyncMock(return_value=single)
    mock_mgr.bangumi.search_id = AsyncMock(return_value=single)

    return mock_mgr, mock_mgr


# ---------------------------------------------------------------------------
# _bangumi_to_dict
# ---------------------------------------------------------------------------


class TestBangumiToDict:
    """Verify _bangumi_to_dict converts a Bangumi model to the expected dict shape."""

    @pytest.fixture
    def sample_bangumi(self) -> Bangumi:
        return make_bangumi(
            id=42,
            official_title="Attack on Titan",
            title_raw="Shingeki no Kyojin",
            season=4,
            group_name="SubsPlease",
            dpi="1080p",
            source="Web",
            subtitle="ENG",
            episode_offset=0,
            season_offset=0,
            filter="720",
            rss_link="https://mikanani.me/RSS/Bangumi/1",
            poster_link="/poster/aot.jpg",
            added=True,
            save_path="/downloads/Attack on Titan",
            deleted=False,
            archived=False,
            eps_collect=False,
        )

    def test_returns_dict(self, sample_bangumi):
        """Result must be a plain dict."""
        result = _bangumi_to_dict(sample_bangumi)
        assert isinstance(result, dict)

    def test_id_field(self, sample_bangumi):
        """id is mapped correctly."""
        assert _bangumi_to_dict(sample_bangumi)["id"] == 42

    def test_official_title_field(self, sample_bangumi):
        """official_title is mapped correctly."""
        assert _bangumi_to_dict(sample_bangumi)["official_title"] == "Attack on Titan"

    def test_title_raw_field(self, sample_bangumi):
        """title_raw is mapped correctly."""
        assert _bangumi_to_dict(sample_bangumi)["title_raw"] == "Shingeki no Kyojin"

    def test_season_field(self, sample_bangumi):
        """season is mapped correctly."""
        assert _bangumi_to_dict(sample_bangumi)["season"] == 4

    def test_episode_offset_field(self, sample_bangumi):
        """episode_offset is present."""
        assert _bangumi_to_dict(sample_bangumi)["episode_offset"] == 0

    def test_season_offset_field(self, sample_bangumi):
        """season_offset is present."""
        assert _bangumi_to_dict(sample_bangumi)["season_offset"] == 0

    def test_rss_link_field(self, sample_bangumi):
        """rss_link is mapped correctly."""
        assert (
            _bangumi_to_dict(sample_bangumi)["rss_link"]
            == "https://mikanani.me/RSS/Bangumi/1"
        )

    def test_deleted_field(self, sample_bangumi):
        """deleted flag is mapped."""
        assert _bangumi_to_dict(sample_bangumi)["deleted"] is False

    def test_archived_field(self, sample_bangumi):
        """archived flag is mapped."""
        assert _bangumi_to_dict(sample_bangumi)["archived"] is False

    def test_eps_collect_field(self, sample_bangumi):
        """eps_collect flag is mapped."""
        assert _bangumi_to_dict(sample_bangumi)["eps_collect"] is False

    def test_all_expected_keys_present(self, sample_bangumi):
        """Every expected key is present in the returned dict."""
        expected_keys = {
            "id",
            "official_title",
            "title_raw",
            "season",
            "group_name",
            "dpi",
            "source",
            "subtitle",
            "episode_offset",
            "season_offset",
            "filter",
            "rss_link",
            "poster_link",
            "added",
            "save_path",
            "deleted",
            "archived",
            "eps_collect",
        }
        result = _bangumi_to_dict(sample_bangumi)
        assert expected_keys.issubset(result.keys())

    def test_none_optional_fields(self):
        """Optional fields that are None are preserved as None."""
        b = make_bangumi(id=1, poster_link=None, save_path=None, group_name=None)
        result = _bangumi_to_dict(b)
        assert result["poster_link"] is None
        assert result["save_path"] is None
        assert result["group_name"] is None


# ---------------------------------------------------------------------------
# TOOLS list
# ---------------------------------------------------------------------------


class TestToolsDefinitions:
    """Sanity-check the static TOOLS list."""

    def test_tools_is_list(self):
        assert isinstance(TOOLS, list)

    def test_tools_not_empty(self):
        assert len(TOOLS) > 0

    def test_all_tools_have_names(self):
        for tool in TOOLS:
            assert tool.name, f"Tool missing name: {tool}"

    def test_expected_tool_names_present(self):
        names = {t.name for t in TOOLS}
        required = {
            "list_anime",
            "get_anime",
            "search_anime",
            "subscribe_anime",
            "unsubscribe_anime",
            "list_downloads",
            "list_rss_feeds",
            "get_program_status",
            "refresh_feeds",
            "update_anime",
        }
        assert required.issubset(names)


# ---------------------------------------------------------------------------
# _dispatch routing
# ---------------------------------------------------------------------------


class TestDispatch:
    """Verify _dispatch delegates to the correct handler for each tool name."""

    # --- list_anime ---

    async def test_dispatch_list_anime_all(self):
        """list_anime without active_only returns all bangumi."""
        bangumi = [make_bangumi(id=1), make_bangumi(id=2, title_raw="Another")]
        ctx = _mock_db(bangumi_list=bangumi)

        with patch("module.mcp.tools.Database", return_value=ctx):
            result = await _dispatch("list_anime", {})

        assert isinstance(result, list)
        assert len(result) == 2

    async def test_dispatch_list_anime_active_only(self):
        """list_anime with active_only=True calls search_all_bangumi."""
        bangumi = [make_bangumi(id=1)]
        ctx, mock_mgr = _mock_sync_manager(bangumi_list=bangumi)

        with patch("module.mcp.tools.TorrentManager", return_value=ctx):
            result = await _dispatch("list_anime", {"active_only": True})

        mock_mgr.search_all_bangumi.assert_called_once()
        assert len(result) == 1

    # --- get_anime ---

    async def test_dispatch_get_anime_found(self):
        """get_anime returns dict when bangumi exists."""
        bangumi = make_bangumi(id=5, official_title="Naruto")
        ctx, _ = _mock_sync_manager(single=bangumi)

        with patch("module.mcp.tools.TorrentManager", return_value=ctx):
            result = await _dispatch("get_anime", {"id": 5})

        assert result["id"] == 5
        assert result["official_title"] == "Naruto"

    async def test_dispatch_get_anime_not_found(self):
        """get_anime returns error dict when lookup fails."""
        not_found = ResponseModel(
            status=False,
            status_code=404,
            msg_en="Not found",
            msg_zh="未找到",
        )
        ctx, _ = _mock_sync_manager(single=not_found)

        with patch("module.mcp.tools.TorrentManager", return_value=ctx):
            result = await _dispatch("get_anime", {"id": 999})

        assert "error" in result
        assert result["error"] == "Not found"

    # --- search_anime ---

    async def test_dispatch_search_anime(self):
        """search_anime calls SearchTorrent.analyse_keyword and returns list."""
        fake_item = json.dumps(
            {"official_title": "One Piece", "rss_link": "https://mikan/rss/1"}
        )

        async def fake_analyse_keyword(keywords, site):
            yield fake_item

        mock_st = AsyncMock()
        mock_st.analyse_keyword = fake_analyse_keyword
        mock_st.__aenter__ = AsyncMock(return_value=mock_st)
        mock_st.__aexit__ = AsyncMock(return_value=False)

        with patch("module.mcp.tools.SearchTorrent", return_value=mock_st):
            result = await _dispatch(
                "search_anime", {"keywords": "One Piece", "site": "mikan"}
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["official_title"] == "One Piece"

    async def test_dispatch_search_anime_default_site(self):
        """search_anime defaults to site='mikan' when site is omitted."""
        captured_site = []

        async def fake_analyse_keyword(keywords, site):
            captured_site.append(site)
            return
            yield  # make it an async generator

        mock_st = AsyncMock()
        mock_st.analyse_keyword = fake_analyse_keyword
        mock_st.__aenter__ = AsyncMock(return_value=mock_st)
        mock_st.__aexit__ = AsyncMock(return_value=False)

        with patch("module.mcp.tools.SearchTorrent", return_value=mock_st):
            await _dispatch("search_anime", {"keywords": "Bleach"})

        assert captured_site == ["mikan"]

    # --- subscribe_anime ---

    async def test_dispatch_subscribe_anime_success(self):
        """subscribe_anime returns status dict on success."""
        fake_bangumi = make_bangumi(id=10)
        fake_resp = _make_response(True, "Subscribed successfully")

        mock_analyser = AsyncMock()
        mock_analyser.link_to_data = AsyncMock(return_value=fake_bangumi)

        with (
            patch("module.mcp.tools.RSSAnalyser", return_value=mock_analyser),
            patch(
                "module.mcp.tools.SeasonCollector.subscribe_season",
                new=AsyncMock(return_value=fake_resp),
            ),
        ):
            result = await _dispatch(
                "subscribe_anime",
                {"rss_link": "https://mikanani.me/RSS/test", "parser": "mikan"},
            )

        assert result["status"] is True
        assert "Subscribed" in result["message"]

    async def test_dispatch_subscribe_anime_failure(self):
        """subscribe_anime returns error when analyser does not return Bangumi."""
        fake_error = ResponseModel(
            status=False, status_code=500, msg_en="Parse failed", msg_zh="解析失败"
        )

        mock_analyser = AsyncMock()
        mock_analyser.link_to_data = AsyncMock(return_value=fake_error)

        with patch("module.mcp.tools.RSSAnalyser", return_value=mock_analyser):
            result = await _dispatch(
                "subscribe_anime",
                {"rss_link": "https://bad-rss.example.com", "parser": "mikan"},
            )

        assert "error" in result

    # --- unsubscribe_anime ---

    async def test_dispatch_unsubscribe_disable(self):
        """unsubscribe_anime with delete=False calls disable_rule."""
        ctx, mock_mgr = _mock_sync_manager()
        mock_mgr.disable_rule = AsyncMock(return_value=_make_response(True, "Disabled"))

        with patch("module.mcp.tools.TorrentManager", return_value=ctx):
            result = await _dispatch("unsubscribe_anime", {"id": 3, "delete": False})

        mock_mgr.disable_rule.assert_called_once_with(3)
        assert result["status"] is True

    async def test_dispatch_unsubscribe_delete(self):
        """unsubscribe_anime with delete=True calls delete_rule."""
        ctx, mock_mgr = _mock_sync_manager()
        mock_mgr.delete_rule = AsyncMock(return_value=_make_response(True, "Deleted"))

        with patch("module.mcp.tools.TorrentManager", return_value=ctx):
            result = await _dispatch("unsubscribe_anime", {"id": 3, "delete": True})

        mock_mgr.delete_rule.assert_called_once_with(3)
        assert result["status"] is True

    # --- list_downloads ---

    async def test_dispatch_list_downloads_all(self):
        """list_downloads with status='all' returns full torrent list."""
        torrent_data = [
            {
                "name": "Ep01.mkv",
                "size": 500,
                "progress": 1.0,
                "state": "completed",
                "dlspeed": 0,
                "upspeed": 0,
                "eta": 0,
            }
        ]
        mock_client = AsyncMock()
        mock_client.get_torrent_info = AsyncMock(return_value=torrent_data)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("module.mcp.tools.DownloadClient", return_value=mock_client):
            result = await _dispatch("list_downloads", {"status": "all"})

        mock_client.get_torrent_info.assert_called_once_with(
            status_filter=None, category="Bangumi"
        )
        assert len(result) == 1
        assert result[0]["name"] == "Ep01.mkv"

    async def test_dispatch_list_downloads_filter_downloading(self):
        """list_downloads with status='downloading' passes filter to client."""
        mock_client = AsyncMock()
        mock_client.get_torrent_info = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("module.mcp.tools.DownloadClient", return_value=mock_client):
            await _dispatch("list_downloads", {"status": "downloading"})

        mock_client.get_torrent_info.assert_called_once_with(
            status_filter="downloading", category="Bangumi"
        )

    async def test_dispatch_list_downloads_keys(self):
        """Each torrent entry contains expected keys only."""
        torrent_data = [
            {
                "name": "Ep02.mkv",
                "size": 800,
                "progress": 0.5,
                "state": "downloading",
                "dlspeed": 1024,
                "upspeed": 512,
                "eta": 3600,
                "extra_key": "should_not_appear",
            }
        ]
        mock_client = AsyncMock()
        mock_client.get_torrent_info = AsyncMock(return_value=torrent_data)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("module.mcp.tools.DownloadClient", return_value=mock_client):
            result = await _dispatch("list_downloads", {})

        expected_keys = {
            "name",
            "size",
            "progress",
            "state",
            "dlspeed",
            "upspeed",
            "eta",
        }
        assert set(result[0].keys()) == expected_keys

    # --- list_rss_feeds ---

    async def test_dispatch_list_rss_feeds(self):
        """list_rss_feeds returns serialised RSS feed list."""
        fake_feed = MagicMock()
        fake_feed.id = 1
        fake_feed.name = "Mikan"
        fake_feed.url = "https://mikanani.me/RSS/test"
        fake_feed.aggregate = True
        fake_feed.parser = "mikan"
        fake_feed.enabled = True
        fake_feed.connection_status = "ok"
        fake_feed.last_checked_at = "2024-01-01T00:00:00"
        fake_feed.last_error = None

        ctx = _mock_db(feeds=[fake_feed])

        with patch("module.mcp.tools.Database", return_value=ctx):
            result = await _dispatch("list_rss_feeds", {})

        assert isinstance(result, list)
        assert result[0]["name"] == "Mikan"
        assert result[0]["url"] == "https://mikanani.me/RSS/test"

    # --- get_program_status ---

    async def test_dispatch_get_program_status(self):
        """get_program_status returns version, running, and first_run."""
        mock_program = MagicMock()
        mock_program.is_running = True
        mock_program.first_run = False

        with (
            patch("module.mcp.tools.VERSION", "3.2.0-beta"),
            patch("module.mcp.tools._get_program_status") as mock_fn,
        ):
            mock_fn.return_value = {
                "version": "3.2.0-beta",
                "running": True,
                "first_run": False,
            }
            result = await _dispatch("get_program_status", {})

        assert "version" in result
        assert "running" in result
        assert "first_run" in result

    # --- refresh_feeds ---

    async def test_dispatch_refresh_feeds(self):
        """refresh_feeds triggers engine.refresh_rss and returns success dict."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.refresh_rss = AsyncMock(return_value=None)

        with (
            patch("module.mcp.tools.DownloadClient", return_value=mock_client),
            patch("module.mcp.tools.RSSEngine", return_value=mock_engine),
        ):
            result = await _dispatch("refresh_feeds", {})

        assert result["status"] is True
        mock_engine.refresh_rss.assert_called_once_with(mock_client)

    # --- update_anime ---

    async def test_dispatch_update_anime_success(self):
        """update_anime applies field overrides and calls update_rule."""
        existing = make_bangumi(id=7, episode_offset=0, season_offset=0, season=1)
        resp = _make_response(True, "Updated")

        db_ctx = _mock_db(single=existing)
        ctx, mock_mgr = _mock_sync_manager()
        mock_mgr.update_rule = AsyncMock(return_value=resp)

        with (
            patch("module.mcp.tools.Database", return_value=db_ctx),
            patch("module.mcp.tools.TorrentManager", return_value=ctx),
        ):
            result = await _dispatch(
                "update_anime",
                {"id": 7, "episode_offset": 12, "season": 2},
            )

        mock_mgr.update_rule.assert_called_once()
        assert result["status"] is True

    async def test_dispatch_update_anime_not_found(self):
        """update_anime returns error dict when bangumi does not exist."""
        ctx, mock_mgr = _mock_sync_manager()
        mock_mgr.bangumi.search_id.return_value = None

        with patch("module.mcp.tools.TorrentManager", return_value=ctx):
            result = await _dispatch("update_anime", {"id": 9999})

        assert "error" in result
        assert "9999" in result["error"]

    # --- unknown tool ---

    async def test_dispatch_unknown_tool(self):
        """An unrecognised tool name returns an error dict."""
        result = await _dispatch("does_not_exist", {})
        assert "error" in result
        assert "does_not_exist" in result["error"]


# ---------------------------------------------------------------------------
# handle_tool wrapper
# ---------------------------------------------------------------------------


class TestHandleTool:
    """Verify handle_tool wraps results correctly and handles exceptions."""

    async def test_handle_tool_returns_text_content_list(self):
        """handle_tool always returns a list of TextContent objects."""
        from mcp import types

        bangumi = [make_bangumi(id=1)]
        ctx = _mock_db(bangumi_list=bangumi)

        with patch("module.mcp.tools.Database", return_value=ctx):
            result = await handle_tool("list_anime", {})

        assert isinstance(result, list)
        assert all(isinstance(item, types.TextContent) for item in result)

    async def test_handle_tool_result_is_valid_json(self):
        """The text in TextContent is valid JSON."""
        bangumi = [make_bangumi(id=1)]
        ctx = _mock_db(bangumi_list=bangumi)

        with patch("module.mcp.tools.Database", return_value=ctx):
            result = await handle_tool("list_anime", {})

        parsed = json.loads(result[0].text)
        assert isinstance(parsed, list)

    async def test_handle_tool_exception_returns_error_json(self):
        """If the underlying handler raises, handle_tool returns a JSON error."""
        with patch(
            "module.mcp.tools._dispatch",
            new=AsyncMock(side_effect=RuntimeError("something broke")),
        ):
            result = await handle_tool("list_anime", {})

        assert len(result) == 1
        body = json.loads(result[0].text)
        assert "error" in body
        assert "something broke" in body["error"]

    async def test_handle_tool_unknown_name_returns_error_json(self):
        """An unknown tool name bubbles up as a JSON error via handle_tool."""
        result = await handle_tool("totally_unknown_tool", {})
        body = json.loads(result[0].text)
        assert "error" in body

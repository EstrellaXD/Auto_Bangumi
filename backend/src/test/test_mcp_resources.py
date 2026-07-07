"""Tests for module.mcp.resources - await handle_resource() and _bangumi_to_dict()."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from module.mcp.resources import (
    RESOURCE_TEMPLATES,
    RESOURCES,
    _bangumi_to_dict,
    handle_resource,
)
from module.models import Bangumi, ResponseModel
from test.factories import make_bangumi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    """Build a MagicMock standing in for a TorrentManager service.

    Used by handlers that call domain methods (e.g. ``search_one``) rather
    than reaching repos off the Database.
    """
    mock_mgr = MagicMock()
    if bangumi_list is not None:
        mock_mgr.bangumi.search_all = AsyncMock(return_value=bangumi_list)
    if single is not None:
        mock_mgr.search_one = AsyncMock(return_value=single)

    return mock_mgr, mock_mgr


def _parse(raw: str) -> dict | list:
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Static metadata (RESOURCES / RESOURCE_TEMPLATES)
# ---------------------------------------------------------------------------


class TestResourceMetadata:
    """Verify the static resource and template lists."""

    async def test_resources_is_list(self):
        assert isinstance(RESOURCES, list)

    async def test_resources_not_empty(self):
        assert len(RESOURCES) > 0

    async def test_resource_uris_present(self):
        uris = {str(r.uri) for r in RESOURCES}
        assert "autobangumi://anime/list" in uris
        assert "autobangumi://status" in uris
        assert "autobangumi://rss/feeds" in uris

    async def test_resource_templates_is_list(self):
        assert isinstance(RESOURCE_TEMPLATES, list)

    async def test_anime_id_template_present(self):
        templates = [str(t.uriTemplate) for t in RESOURCE_TEMPLATES]
        assert "autobangumi://anime/{id}" in templates


# ---------------------------------------------------------------------------
# _bangumi_to_dict (resources module version)
# ---------------------------------------------------------------------------


class TestBangumiToDictResources:
    """
    resources._bangumi_to_dict is a leaner version of the tools one
    (no dpi/source/subtitle/group_name fields).
    """

    @pytest.fixture
    def sample(self) -> Bangumi:
        return make_bangumi(
            id=10,
            official_title="Demon Slayer",
            title_raw="Kimetsu no Yaiba",
            season=3,
            episode_offset=2,
            season_offset=1,
            filter="720",
            rss_link="https://mikanani.me/RSS/ds",
            poster_link="/poster/ds.jpg",
            added=True,
            save_path="/downloads/Demon Slayer",
            deleted=False,
            archived=False,
            eps_collect=True,
        )

    async def test_returns_dict(self, sample):
        assert isinstance(_bangumi_to_dict(sample), dict)

    async def test_required_keys_present(self, sample):
        result = _bangumi_to_dict(sample)
        required = {
            "id",
            "official_title",
            "title_raw",
            "season",
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
        assert required.issubset(result.keys())

    async def test_id_value(self, sample):
        assert _bangumi_to_dict(sample)["id"] == 10

    async def test_official_title_value(self, sample):
        assert _bangumi_to_dict(sample)["official_title"] == "Demon Slayer"

    async def test_eps_collect_true(self, sample):
        assert _bangumi_to_dict(sample)["eps_collect"] is True

    async def test_none_optional_poster(self):
        b = make_bangumi(id=1, poster_link=None)
        assert _bangumi_to_dict(b)["poster_link"] is None


# ---------------------------------------------------------------------------
# handle_resource - known static URIs
# ---------------------------------------------------------------------------


class TestHandleResourceAnimeList:
    """Tests for autobangumi://anime/list."""

    async def test_returns_json_string(self):
        """Result is a valid JSON string."""
        ctx = _mock_db(bangumi_list=[])
        with patch("module.mcp.resources.Database", return_value=ctx):
            raw = await handle_resource("autobangumi://anime/list")
        assert isinstance(raw, str)
        _parse(raw)  # must not raise

    async def test_empty_database_returns_empty_list(self):
        """Empty DB produces an empty JSON array."""
        ctx = _mock_db(bangumi_list=[])
        with patch("module.mcp.resources.Database", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://anime/list"))
        assert result == []

    async def test_multiple_bangumi_serialised(self):
        """Multiple Bangumi entries all appear in the output list."""
        bangumi = [make_bangumi(id=1), make_bangumi(id=2, title_raw="Other")]
        ctx = _mock_db(bangumi_list=bangumi)
        with patch("module.mcp.resources.Database", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://anime/list"))
        assert len(result) == 2

    async def test_ids_are_in_output(self):
        """Each serialised entry contains its correct id."""
        bangumi = [make_bangumi(id=7), make_bangumi(id=8, title_raw="B")]
        ctx = _mock_db(bangumi_list=bangumi)
        with patch("module.mcp.resources.Database", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://anime/list"))
        ids = {item["id"] for item in result}
        assert {7, 8}.issubset(ids)

    async def test_non_ascii_titles_preserved(self):
        """Japanese/Chinese titles survive JSON serialisation."""
        bangumi = [make_bangumi(id=1, official_title="進撃の巨人")]
        ctx = _mock_db(bangumi_list=bangumi)
        with patch("module.mcp.resources.Database", return_value=ctx):
            raw = await handle_resource("autobangumi://anime/list")
        # ensure_ascii=False means the characters appear verbatim
        assert "進撃の巨人" in raw


class TestHandleResourceStatus:
    """Tests for autobangumi://status."""

    @pytest.fixture
    def mock_program(self):
        prog = MagicMock()
        prog.is_running = True
        prog.first_run = False
        return prog

    async def test_returns_json_string(self, mock_program):
        with (
            patch("module.mcp.resources.VERSION", "3.2.0-test"),
            patch("module.mcp.resources.get_context", return_value=mock_program),
        ):
            raw = await handle_resource("autobangumi://status")
        assert isinstance(raw, str)
        _parse(raw)

    async def test_version_in_output(self, mock_program):
        with (
            patch("module.mcp.resources.VERSION", "3.2.0-test"),
            patch("module.mcp.resources.get_context", return_value=mock_program),
        ):
            result = _parse(await handle_resource("autobangumi://status"))
        assert isinstance(result, dict)
        assert result["version"] == "3.2.0-test"

    async def test_running_true(self, mock_program):
        mock_program.is_running = True
        with (
            patch("module.mcp.resources.VERSION", "3.2.0-test"),
            patch("module.mcp.resources.get_context", return_value=mock_program),
        ):
            result = _parse(await handle_resource("autobangumi://status"))
        assert isinstance(result, dict)
        assert result["running"] is True

    async def test_first_run_false(self, mock_program):
        mock_program.first_run = False
        with (
            patch("module.mcp.resources.VERSION", "3.2.0-test"),
            patch("module.mcp.resources.get_context", return_value=mock_program),
        ):
            result = _parse(await handle_resource("autobangumi://status"))
        assert isinstance(result, dict)
        assert result["first_run"] is False

    async def test_all_keys_present(self, mock_program):
        with (
            patch("module.mcp.resources.VERSION", "3.2.0-test"),
            patch("module.mcp.resources.get_context", return_value=mock_program),
        ):
            result = _parse(await handle_resource("autobangumi://status"))
        assert isinstance(result, dict)
        assert {"version", "running", "first_run"}.issubset(result.keys())


class TestHandleResourceRssFeeds:
    """Tests for autobangumi://rss/feeds."""

    def _make_feed(self, feed_id=1, name="TestFeed", url="https://example.com/rss"):
        f = MagicMock()
        f.id = feed_id
        f.name = name
        f.url = url
        f.enabled = True
        f.connection_status = "ok"
        f.last_checked_at = "2024-01-01T00:00:00"
        return f

    async def test_returns_json_string(self):
        ctx = _mock_db(feeds=[])
        with patch("module.mcp.resources.Database", return_value=ctx):
            raw = await handle_resource("autobangumi://rss/feeds")
        assert isinstance(raw, str)
        _parse(raw)

    async def test_empty_feeds_returns_empty_list(self):
        ctx = _mock_db(feeds=[])
        with patch("module.mcp.resources.Database", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://rss/feeds"))
        assert result == []

    async def test_feed_fields_present(self):
        feed = self._make_feed(feed_id=2, name="Mikan", url="https://mikanani.me/rss")
        ctx = _mock_db(feeds=[feed])
        with patch("module.mcp.resources.Database", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://rss/feeds"))
        entry = result[0]
        assert entry["id"] == 2
        assert entry["name"] == "Mikan"
        assert entry["url"] == "https://mikanani.me/rss"
        assert "enabled" in entry
        assert "connection_status" in entry
        assert "last_checked_at" in entry

    async def test_multiple_feeds(self):
        feeds = [
            self._make_feed(1, "Feed A", "https://a.example.com/rss"),
            self._make_feed(2, "Feed B", "https://b.example.com/rss"),
        ]
        ctx = _mock_db(feeds=feeds)
        with patch("module.mcp.resources.Database", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://rss/feeds"))
        assert len(result) == 2


# ---------------------------------------------------------------------------
# handle_resource - anime/{id} template
# ---------------------------------------------------------------------------


class TestHandleResourceAnimeById:
    """Tests for the autobangumi://anime/{id} template."""

    async def test_valid_id_returns_bangumi_dict(self):
        """A numeric ID resolves to the bangumi's serialised dict."""
        bangumi = make_bangumi(id=3, official_title="Fullmetal Alchemist")
        ctx, _ = _mock_sync_manager(single=bangumi)
        with patch("module.mcp.resources.TorrentManager", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://anime/3"))
        assert isinstance(result, dict)
        assert result["id"] == 3
        assert result["official_title"] == "Fullmetal Alchemist"

    async def test_not_found_id_returns_error(self):
        """When search_one returns a ResponseModel, result contains 'error'."""
        not_found = ResponseModel(
            status=False, status_code=404, msg_en="Anime not found", msg_zh="未找到"
        )
        ctx, _ = _mock_sync_manager(single=not_found)
        with patch("module.mcp.resources.TorrentManager", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://anime/9999"))
        assert "error" in result

    async def test_non_numeric_id_returns_error(self):
        """A non-integer ID segment produces a JSON error without crashing."""
        result = _parse(await handle_resource("autobangumi://anime/abc"))
        assert isinstance(result, dict)
        assert "error" in result
        assert "abc" in result["error"]

    async def test_negative_id_is_passed_to_manager(self):
        """Negative integers are valid integers and passed through."""
        not_found = ResponseModel(
            status=False, status_code=404, msg_en="Anime not found", msg_zh="未找到"
        )
        ctx, mock_mgr = _mock_sync_manager(single=not_found)
        with patch("module.mcp.resources.TorrentManager", return_value=ctx):
            await handle_resource("autobangumi://anime/-1")
        mock_mgr.search_one.assert_called_once_with(-1)

    async def test_result_has_required_fields(self):
        """Returned dict contains all expected bangumi fields."""
        bangumi = make_bangumi(id=5)
        ctx, _ = _mock_sync_manager(single=bangumi)
        with patch("module.mcp.resources.TorrentManager", return_value=ctx):
            result = _parse(await handle_resource("autobangumi://anime/5"))
        assert isinstance(result, dict)
        required = {"id", "official_title", "title_raw", "season", "rss_link"}
        assert required.issubset(result.keys())


# ---------------------------------------------------------------------------
# handle_resource - unknown URI
# ---------------------------------------------------------------------------


class TestHandleResourceUnknown:
    """Tests for unrecognised resource URIs."""

    async def test_unknown_uri_returns_json_error(self):
        """An unrecognised URI produces a JSON object with 'error'."""
        result = _parse(await handle_resource("autobangumi://does/not/exist"))
        assert "error" in result

    async def test_unknown_uri_mentions_uri_in_error(self):
        """The error message includes the unrecognised URI."""
        uri = "autobangumi://does/not/exist"
        result = _parse(await handle_resource(uri))
        assert isinstance(result, dict)
        assert uri in result["error"]

    async def test_empty_uri_returns_error(self):
        """An empty string URI returns a JSON error."""
        result = _parse(await handle_resource(""))
        assert "error" in result

    async def test_completely_different_scheme_returns_error(self):
        """A URI with a wrong scheme returns a JSON error."""
        result = _parse(
            await handle_resource("https://autobangumi.example.com/anime/list")
        )
        assert "error" in result

"""Tests for RSS API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.database import get_db
from module.models import (
    Bangumi,
    Movie,
    RSSPreviewItem,
    RSSPreviewResponse,
    ResponseModel,
    RSSItem,
    RSSUpdate,
    Torrent,
)
from module.security.api import get_current_user
from test.factories import make_bangumi, make_rss_item, make_torrent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """A stand-in Database whose repos can be configured with AsyncMocks."""
    return MagicMock()


@pytest.fixture
def app(mock_db):
    app = FastAPI()
    app.include_router(v1, prefix="/api")

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture
def authed_client(app):
    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_get_rss_unauthorized(self, unauthed_client):
        """GET /rss without auth returns 401."""
        response = unauthed_client.get("/api/v1/rss")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_add_rss_unauthorized(self, unauthed_client):
        """POST /rss/add without auth returns 401."""
        response = unauthed_client.post(
            "/api/v1/rss/add", json={"url": "https://test.com"}
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /rss
# ---------------------------------------------------------------------------


class TestGetRss:
    def test_get_all(self, authed_client, mock_db):
        """GET /rss returns list of RSSItems."""
        items = [
            make_rss_item(id=1, name="Feed 1"),
            make_rss_item(id=2, name="Feed 2"),
        ]
        mock_db.rss.search_all = AsyncMock(return_value=items)

        response = authed_client.get("/api/v1/rss")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


# ---------------------------------------------------------------------------
# POST /rss/add
# ---------------------------------------------------------------------------


class TestAddRss:
    def test_add_success(self, authed_client):
        """POST /rss/add creates a new RSS feed."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Added.", msg_zh="添加成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MockEngine.return_value
            mock_eng.add_rss = AsyncMock(return_value=resp_model)

            response = authed_client.post(
                "/api/v1/rss/add",
                json={
                    "url": "https://mikanani.me/RSS/test",
                    "name": "Test Feed",
                    "aggregate": True,
                    "parser": "mikan",
                },
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# DELETE /rss/delete/{id}
# ---------------------------------------------------------------------------


class TestDeleteRss:
    def test_delete_success(self, authed_client, mock_db):
        """DELETE /rss/delete/{id} removes the feed."""
        mock_db.rss.delete = AsyncMock(return_value=True)

        response = authed_client.delete("/api/v1/rss/delete/1")

        assert response.status_code == 200

    def test_delete_failure(self, authed_client, mock_db):
        """DELETE /rss/delete/{id} returns 400 when feed not found."""
        mock_db.rss.delete = AsyncMock(return_value=False)

        response = authed_client.delete("/api/v1/rss/delete/999")

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /rss/disable/{id}
# ---------------------------------------------------------------------------


class TestDisableRss:
    def test_disable_success(self, authed_client, mock_db):
        """PATCH /rss/disable/{id} disables the feed."""
        mock_db.rss.disable = AsyncMock(return_value=True)

        response = authed_client.patch("/api/v1/rss/disable/1")

        assert response.status_code == 200

    def test_disable_failure(self, authed_client, mock_db):
        """PATCH /rss/disable/{id} returns 404 when feed not found."""
        mock_db.rss.disable = AsyncMock(return_value=False)

        response = authed_client.patch("/api/v1/rss/disable/999")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /rss/enable/many, /rss/disable/many, /rss/delete/many
# ---------------------------------------------------------------------------


class TestBatchOperations:
    def test_enable_many(self, authed_client):
        """POST /rss/enable/many enables multiple feeds."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Enabled.", msg_zh="启用成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MockEngine.return_value
            mock_eng.enable_list = AsyncMock(return_value=resp_model)

            response = authed_client.post("/api/v1/rss/enable/many", json=[1, 2, 3])

        assert response.status_code == 200

    def test_disable_many(self, authed_client):
        """POST /rss/disable/many disables multiple feeds."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Disabled.", msg_zh="禁用成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MockEngine.return_value
            mock_eng.disable_list = AsyncMock(return_value=resp_model)

            response = authed_client.post("/api/v1/rss/disable/many", json=[1, 2])

        assert response.status_code == 200

    def test_delete_many(self, authed_client):
        """POST /rss/delete/many deletes multiple feeds."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Deleted.", msg_zh="删除成功。"
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MockEngine.return_value
            mock_eng.delete_list = AsyncMock(return_value=resp_model)

            response = authed_client.post("/api/v1/rss/delete/many", json=[1, 2])

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /rss/update/{id}
# ---------------------------------------------------------------------------


class TestUpdateRss:
    def test_update_success(self, authed_client, mock_db):
        """PATCH /rss/update/{id} updates feed."""
        mock_db.rss.update = AsyncMock(return_value=True)

        response = authed_client.patch(
            "/api/v1/rss/update/1",
            json={"name": "Updated Name", "aggregate": False},
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /rss/refresh/*
# ---------------------------------------------------------------------------


class TestRefreshRss:
    def test_refresh_all(self, authed_client):
        """POST /rss/refresh/all triggers engine.refresh_rss."""
        with patch("module.api.rss.DownloadClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("module.api.rss.RSSEngine") as MockEngine:
                mock_eng = MockEngine.return_value
                mock_eng.refresh_rss = AsyncMock()

                response = authed_client.post("/api/v1/rss/refresh/all")

        assert response.status_code == 200

    def test_refresh_single(self, authed_client):
        """POST /rss/refresh/{id} refreshes specific feed."""
        with patch("module.api.rss.DownloadClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("module.api.rss.RSSEngine") as MockEngine:
                mock_eng = MockEngine.return_value
                mock_eng.refresh_rss = AsyncMock()

                response = authed_client.post("/api/v1/rss/refresh/1")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /rss/torrent/{id}
# ---------------------------------------------------------------------------


class TestGetRssTorrents:
    def test_get_torrents(self, authed_client):
        """GET /rss/torrent/{id} returns torrents for that feed."""
        torrents = [make_torrent(id=1, rss_id=1), make_torrent(id=2, rss_id=1)]
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MockEngine.return_value
            mock_eng.get_rss_torrents = AsyncMock(return_value=torrents)

            response = authed_client.get("/api/v1/rss/torrent/1")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


# ---------------------------------------------------------------------------
# POST /rss/preview
# ---------------------------------------------------------------------------


class TestPreviewRss:
    def test_preview_rss(self, authed_client):
        """POST /rss/preview returns preview rows for an arbitrary feed URL."""
        preview = RSSPreviewResponse(
            items=[
                RSSPreviewItem(
                    name="[Sub] Test Anime - 01 [1080p].mkv",
                    url="https://example.com/1.torrent",
                    homepage="https://example.com/1",
                ),
                RSSPreviewItem(
                    name="[Sub] Test Anime - 01 [720p].mkv",
                    url="https://example.com/2.torrent",
                    homepage=None,
                ),
            ],
            global_filter=["720"],
        )
        with patch("module.api.rss.RSSEngine") as MockEngine:
            mock_eng = MockEngine.return_value
            mock_eng.preview_rss = AsyncMock(return_value=preview)

            response = authed_client.post(
                "/api/v1/rss/preview",
                json={"rss_link": "https://mikanani.me/RSS/Search?searchstr=test"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["global_filter"] == ["720"]
        assert [row["name"] for row in data["items"]] == [
            "[Sub] Test Anime - 01 [1080p].mkv",
            "[Sub] Test Anime - 01 [720p].mkv",
        ]


# ---------------------------------------------------------------------------
# POST /rss/analysis
# ---------------------------------------------------------------------------


class TestAnalysis:
    def test_analysis_returns_bangumi(self, authed_client):
        """POST /rss/analysis returns the parsed Bangumi on success."""
        bangumi = make_bangumi(id=1, official_title="Parsed Anime")
        with patch("module.api.rss.analyser") as mock_analyser:
            mock_analyser.link_to_data = AsyncMock(return_value=bangumi)

            response = authed_client.post(
                "/api/v1/rss/analysis",
                json={"url": "https://mikanani.me/RSS/link", "parser": "mikan"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["official_title"] == "Parsed Anime"

    def test_analysis_returns_movie(self, authed_client):
        """POST /rss/analysis preserves a parsed movie response."""
        movie = Movie(official_title="Parsed Movie", title_raw="Parsed Movie")
        with patch("module.api.rss.analyser") as mock_analyser:
            mock_analyser.link_to_data = AsyncMock(return_value=movie)

            response = authed_client.post(
                "/api/v1/rss/analysis",
                json={"url": "https://mikanani.me/RSS/link", "parser": "mikan"},
            )

        assert response.status_code == 200
        assert response.json()["official_title"] == "Parsed Movie"


# ---------------------------------------------------------------------------
# POST /rss/collect
# ---------------------------------------------------------------------------


class TestCollect:
    def test_collect_success(self, authed_client):
        """POST /rss/collect triggers SeasonCollector.collect_season."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Collected.", msg_zh="收集成功。"
        )
        with (
            patch("module.api.rss.DownloadClient") as MockDC,
            patch("module.api.rss.SeasonCollector") as MockCollector,
        ):
            MockDC.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            MockDC.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_collector = MagicMock()
            mock_collector.collect_season = AsyncMock(return_value=resp_model)
            MockCollector.return_value = mock_collector

            response = authed_client.post(
                "/api/v1/rss/collect", json=make_bangumi(id=1).model_dump()
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /rss/subscribe
# ---------------------------------------------------------------------------


class TestSubscribe:
    def test_subscribe_success(self, authed_client):
        """POST /rss/subscribe triggers SeasonCollector.subscribe_season."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Subscribed.", msg_zh="订阅成功。"
        )
        with patch(
            "module.api.rss.SeasonCollector.subscribe_season",
            new_callable=AsyncMock,
            return_value=resp_model,
        ):
            response = authed_client.post(
                "/api/v1/rss/subscribe",
                json={
                    "data": make_bangumi(id=1).model_dump(),
                    "rss": {"url": "https://mikanani.me/RSS/link", "parser": "mikan"},
                },
            )

        assert response.status_code == 200

    _PROVIDERS = {
        "mikan": {
            "url": "https://mikanani.me/RSS/Search?searchstr=%s",
            "parser": "mikan",
        },
        "nyaa": {"url": "https://nyaa.si/?page=rss&q=%s", "parser": "tmdb"},
    }

    def test_subscribe_site_name_maps_to_provider_parser(self, authed_client):
        """搜索订阅传入站点名（如 nyaa）时应映射为该站点配置的解析器（#1053）。"""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Subscribed.", msg_zh="订阅成功。"
        )
        with (
            patch(
                "module.api.rss.SeasonCollector.subscribe_season",
                new_callable=AsyncMock,
                return_value=resp_model,
            ) as mock_subscribe,
            patch("module.api.rss.get_provider", return_value=self._PROVIDERS),
        ):
            response = authed_client.post(
                "/api/v1/rss/subscribe",
                json={
                    "data": make_bangumi(id=1).model_dump(),
                    "rss": {"url": "https://nyaa.si/?page=rss&q=x", "parser": "nyaa"},
                },
            )

        assert response.status_code == 200
        assert mock_subscribe.await_args is not None
        assert mock_subscribe.await_args.kwargs["parser"] == "tmdb"

    def test_subscribe_parser_value_passes_through_unchanged(self, authed_client):
        """已是解析器类型的值（非站点名）应原样传递。"""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Subscribed.", msg_zh="订阅成功。"
        )
        with (
            patch(
                "module.api.rss.SeasonCollector.subscribe_season",
                new_callable=AsyncMock,
                return_value=resp_model,
            ) as mock_subscribe,
            patch("module.api.rss.get_provider", return_value=self._PROVIDERS),
        ):
            response = authed_client.post(
                "/api/v1/rss/subscribe",
                json={
                    "data": make_bangumi(id=1).model_dump(),
                    "rss": {"url": "https://example.com/rss", "parser": "tmdb"},
                },
            )

        assert response.status_code == 200
        assert mock_subscribe.await_args is not None
        assert mock_subscribe.await_args.kwargs["parser"] == "tmdb"

    def test_subscribe_known_parser_type_never_remapped(self, authed_client):
        """parser='mikan' 是解析器类型而非站点名，即便用户自定义了 mikan
        站点的解析器（如 tmdb），也不应被站点映射改写。"""
        customized = {
            "mikan": {
                "url": "https://mikanani.me/RSS/Search?searchstr=%s",
                "parser": "tmdb",
            },
        }
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Subscribed.", msg_zh="订阅成功。"
        )
        with (
            patch(
                "module.api.rss.SeasonCollector.subscribe_season",
                new_callable=AsyncMock,
                return_value=resp_model,
            ) as mock_subscribe,
            patch("module.api.rss.get_provider", return_value=customized),
        ):
            response = authed_client.post(
                "/api/v1/rss/subscribe",
                json={
                    "data": make_bangumi(id=1).model_dump(),
                    "rss": {"url": "https://mikanani.me/RSS/link", "parser": "mikan"},
                },
            )

        assert response.status_code == 200
        assert mock_subscribe.await_args is not None
        assert mock_subscribe.await_args.kwargs["parser"] == "mikan"

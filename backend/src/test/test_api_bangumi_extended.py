"""Tests for extended Bangumi API endpoints (archive, refresh, offset, batch)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.models import Bangumi, ResponseModel
from module.security.api import get_current_user

from test.factories import make_bangumi


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a FastAPI app with v1 routes for testing."""
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    return app


@pytest.fixture
def authed_client(app):
    """TestClient with auth dependency overridden."""

    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client(app):
    """TestClient without auth (no override)."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Archive endpoints
# ---------------------------------------------------------------------------


class TestArchiveBangumi:
    def test_archive_success(self, authed_client):
        """PATCH /bangumi/archive/{id} archives a bangumi."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Archived.", msg_zh="已归档。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.archive_rule.return_value = resp_model
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.patch("/api/v1/bangumi/archive/1")

        assert response.status_code == 200

    def test_unarchive_success(self, authed_client):
        """PATCH /bangumi/unarchive/{id} unarchives a bangumi."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Unarchived.", msg_zh="已取消归档。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.unarchive_rule.return_value = resp_model
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.patch("/api/v1/bangumi/unarchive/1")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Refresh endpoints
# ---------------------------------------------------------------------------


class TestRefreshBangumi:
    def test_refresh_poster_all(self, authed_client):
        """GET /bangumi/refresh/poster/all refreshes all posters."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Refreshed.", msg_zh="已刷新。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.refresh_poster = AsyncMock(return_value=resp_model)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/refresh/poster/all")

        assert response.status_code == 200

    def test_refresh_poster_one(self, authed_client):
        """GET /bangumi/refresh/poster/{id} refreshes single poster."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Refreshed.", msg_zh="已刷新。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.refind_poster = AsyncMock(return_value=resp_model)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/refresh/poster/1")

        assert response.status_code == 200

    def test_refresh_calendar(self, authed_client):
        """GET /bangumi/refresh/calendar refreshes calendar data."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Refreshed.", msg_zh="已刷新。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.refresh_calendar = AsyncMock(return_value=resp_model)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/refresh/calendar")

        assert response.status_code == 200

    def test_refresh_metadata(self, authed_client):
        """GET /bangumi/refresh/metadata refreshes TMDB metadata."""
        resp_model = ResponseModel(
            status=True, status_code=200, msg_en="Refreshed.", msg_zh="已刷新。"
        )
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.refresh_metadata = AsyncMock(return_value=resp_model)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/refresh/metadata")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Offset endpoints
# ---------------------------------------------------------------------------


class TestOffsetDetection:
    def test_suggest_offset(self, authed_client):
        """GET /bangumi/suggest-offset/{id} returns offset suggestion."""
        suggestion = {"suggested_offset": 12, "reason": "Season 2 starts at episode 13"}
        with patch("module.api.bangumi.TorrentManager") as MockManager:
            mock_mgr = MagicMock()
            mock_mgr.suggest_offset = AsyncMock(return_value=suggestion)
            MockManager.return_value.__enter__ = MagicMock(return_value=mock_mgr)
            MockManager.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/suggest-offset/1")

        assert response.status_code == 200
        data = response.json()
        assert data["suggested_offset"] == 12

    def test_detect_offset_no_mismatch(self, authed_client):
        """POST /bangumi/detect-offset with no mismatch."""
        mock_tmdb_info = MagicMock()
        mock_tmdb_info.title = "Test Anime"
        mock_tmdb_info.last_season = 1
        mock_tmdb_info.season_episode_counts = {1: 12}
        mock_tmdb_info.series_status = "Ended"
        mock_tmdb_info.virtual_season_starts = None

        with patch("module.api.bangumi.tmdb_parser", return_value=mock_tmdb_info):
            with patch("module.api.bangumi.detect_offset_mismatch", return_value=None):
                response = authed_client.post(
                    "/api/v1/bangumi/detect-offset",
                    json={
                        "title": "Test Anime",
                        "parsed_season": 1,
                        "parsed_episode": 5,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["has_mismatch"] is False
        assert data["suggestion"] is None

    def test_detect_offset_with_mismatch(self, authed_client):
        """POST /bangumi/detect-offset with mismatch detected."""
        mock_tmdb_info = MagicMock()
        mock_tmdb_info.title = "Test Anime"
        mock_tmdb_info.last_season = 2
        mock_tmdb_info.season_episode_counts = {1: 12, 2: 12}
        mock_tmdb_info.series_status = "Returning"
        mock_tmdb_info.virtual_season_starts = None

        mock_suggestion = MagicMock()
        mock_suggestion.season_offset = 1
        mock_suggestion.episode_offset = 12
        mock_suggestion.reason = "Detected multi-season broadcast"
        mock_suggestion.confidence = "high"

        with patch("module.api.bangumi.tmdb_parser", return_value=mock_tmdb_info):
            with patch(
                "module.api.bangumi.detect_offset_mismatch",
                return_value=mock_suggestion,
            ):
                response = authed_client.post(
                    "/api/v1/bangumi/detect-offset",
                    json={
                        "title": "Test Anime",
                        "parsed_season": 1,
                        "parsed_episode": 25,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["has_mismatch"] is True
        assert data["suggestion"]["episode_offset"] == 12

    def test_detect_offset_no_tmdb_data(self, authed_client):
        """POST /bangumi/detect-offset when TMDB has no data."""
        with patch("module.api.bangumi.tmdb_parser", return_value=None):
            response = authed_client.post(
                "/api/v1/bangumi/detect-offset",
                json={
                    "title": "Unknown Anime",
                    "parsed_season": 1,
                    "parsed_episode": 5,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["has_mismatch"] is False
        assert data["tmdb_info"] is None


# ---------------------------------------------------------------------------
# Needs review endpoints
# ---------------------------------------------------------------------------


class TestNeedsReview:
    def test_get_needs_review(self, authed_client):
        """GET /bangumi/needs-review returns bangumi needing review."""
        bangumi_list = [
            make_bangumi(id=1, official_title="Anime 1"),
            make_bangumi(id=2, official_title="Anime 2"),
        ]
        with patch("module.api.bangumi.Database") as MockDB:
            mock_db = MagicMock()
            mock_db.bangumi.get_needs_review.return_value = bangumi_list
            MockDB.return_value.__enter__ = MagicMock(return_value=mock_db)
            MockDB.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.get("/api/v1/bangumi/needs-review")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_dismiss_review_success(self, authed_client):
        """POST /bangumi/dismiss-review/{id} clears review flag."""
        with patch("module.api.bangumi.Database") as MockDB:
            mock_db = MagicMock()
            mock_db.bangumi.clear_needs_review.return_value = True
            MockDB.return_value.__enter__ = MagicMock(return_value=mock_db)
            MockDB.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.post("/api/v1/bangumi/dismiss-review/1")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True

    def test_dismiss_review_not_found(self, authed_client):
        """POST /bangumi/dismiss-review/{id} with non-existent bangumi."""
        with patch("module.api.bangumi.Database") as MockDB:
            mock_db = MagicMock()
            mock_db.bangumi.clear_needs_review.return_value = False
            MockDB.return_value.__enter__ = MagicMock(return_value=mock_db)
            MockDB.return_value.__exit__ = MagicMock(return_value=False)

            response = authed_client.post("/api/v1/bangumi/dismiss-review/999")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


class TestBatchOperations:
    def test_delete_many_auth_required(self, unauthed_client):
        """DELETE /bangumi/delete/many/ requires authentication."""
        # Note: The batch endpoints accept list as body but FastAPI requires
        # proper Query/Body annotations. Testing auth requirement only.
        with patch("module.security.api.DEV_AUTH_BYPASS", False):
            response = unauthed_client.request(
                "DELETE",
                "/api/v1/bangumi/delete/many/",
                json=[1, 2, 3],
            )
        assert response.status_code == 401

    def test_disable_many_auth_required(self, unauthed_client):
        """DELETE /bangumi/disable/many/ requires authentication."""
        with patch("module.security.api.DEV_AUTH_BYPASS", False):
            response = unauthed_client.request(
                "DELETE",
                "/api/v1/bangumi/disable/many/",
                json=[1, 2],
            )
        assert response.status_code == 401

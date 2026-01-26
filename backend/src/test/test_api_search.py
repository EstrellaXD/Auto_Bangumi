"""Tests for Search API endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.security.api import get_current_user


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
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_search_bangumi_unauthorized(self, unauthed_client):
        """GET /search/bangumi without auth returns 401."""
        response = unauthed_client.get(
            "/api/v1/search/bangumi", params={"keywords": "test"}
        )
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_search_provider_unauthorized(self, unauthed_client):
        """GET /search/provider without auth returns 401."""
        response = unauthed_client.get("/api/v1/search/provider")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_get_provider_config_unauthorized(self, unauthed_client):
        """GET /search/provider/config without auth returns 401."""
        response = unauthed_client.get("/api/v1/search/provider/config")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /search/bangumi (SSE endpoint)
# ---------------------------------------------------------------------------


class TestSearchBangumi:
    def test_search_no_keywords(self, authed_client):
        """GET /search/bangumi without keywords returns empty list."""
        response = authed_client.get("/api/v1/search/bangumi")
        # SSE endpoint returns EventSourceResponse for empty
        assert response.status_code == 200

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_search_with_keywords_auth_required(self, unauthed_client):
        """GET /search/bangumi requires authentication."""
        response = unauthed_client.get(
            "/api/v1/search/bangumi",
            params={"site": "mikan", "keywords": "Test Anime"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /search/provider
# ---------------------------------------------------------------------------


class TestSearchProvider:
    def test_get_provider_list(self, authed_client):
        """GET /search/provider returns list of available providers."""
        mock_config = {"mikan": "url1", "dmhy": "url2", "nyaa": "url3"}
        with patch("module.api.search.SEARCH_CONFIG", mock_config):
            response = authed_client.get("/api/v1/search/provider")

        assert response.status_code == 200
        data = response.json()
        assert "mikan" in data
        assert "dmhy" in data
        assert "nyaa" in data


# ---------------------------------------------------------------------------
# GET /search/provider/config
# ---------------------------------------------------------------------------


class TestSearchProviderConfig:
    def test_get_provider_config(self, authed_client):
        """GET /search/provider/config returns provider configurations."""
        mock_providers = {
            "mikan": "https://mikanani.me/RSS/Search?searchstr={keyword}",
            "dmhy": "https://share.dmhy.org/search?keyword={keyword}",
        }
        with patch("module.api.search.get_provider", return_value=mock_providers):
            response = authed_client.get("/api/v1/search/provider/config")

        assert response.status_code == 200
        data = response.json()
        assert "mikan" in data
        assert "dmhy" in data


# ---------------------------------------------------------------------------
# PUT /search/provider/config
# ---------------------------------------------------------------------------


class TestUpdateProviderConfig:
    def test_update_provider_config_success(self, authed_client):
        """PUT /search/provider/config updates provider configurations."""
        new_config = {
            "mikan": "https://mikanani.me/RSS/Search?searchstr={keyword}",
            "custom": "https://custom.site/search?q={keyword}",
        }
        with patch("module.api.search.save_provider") as mock_save:
            with patch("module.api.search.get_provider", return_value=new_config):
                response = authed_client.put(
                    "/api/v1/search/provider/config", json=new_config
                )

        assert response.status_code == 200
        mock_save.assert_called_once_with(new_config)
        data = response.json()
        assert "mikan" in data
        assert "custom" in data

    def test_update_provider_config_empty(self, authed_client):
        """PUT /search/provider/config with empty config."""
        with patch("module.api.search.save_provider") as mock_save:
            with patch("module.api.search.get_provider", return_value={}):
                response = authed_client.put("/api/v1/search/provider/config", json={})

        assert response.status_code == 200
        mock_save.assert_called_once_with({})

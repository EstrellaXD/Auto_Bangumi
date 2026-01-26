"""Tests for Config API endpoints."""

import pytest
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.models.config import Config
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


@pytest.fixture
def mock_settings():
    """Mock settings object."""
    settings = MagicMock(spec=Config)
    settings.program = MagicMock()
    settings.program.rss_time = 900
    settings.program.rename_time = 60
    settings.program.webui_port = 7892
    settings.downloader = MagicMock()
    settings.downloader.type = "qbittorrent"
    settings.downloader.host = "172.17.0.1:8080"
    settings.downloader.username = "admin"
    settings.downloader.password = "adminadmin"
    settings.downloader.path = "/downloads/Bangumi"
    settings.downloader.ssl = False
    settings.rss_parser = MagicMock()
    settings.rss_parser.enable = True
    settings.rss_parser.filter = ["720", r"\d+-\d"]
    settings.rss_parser.language = "zh"
    settings.bangumi_manage = MagicMock()
    settings.bangumi_manage.enable = True
    settings.bangumi_manage.eps_complete = False
    settings.bangumi_manage.rename_method = "pn"
    settings.bangumi_manage.group_tag = False
    settings.bangumi_manage.remove_bad_torrent = False
    settings.log = MagicMock()
    settings.log.debug_enable = False
    settings.proxy = MagicMock()
    settings.proxy.enable = False
    settings.notification = MagicMock()
    settings.notification.enable = False
    settings.experimental_openai = MagicMock()
    settings.experimental_openai.enable = False
    settings.save = MagicMock()
    settings.load = MagicMock()
    return settings


# ---------------------------------------------------------------------------
# Auth requirement
# ---------------------------------------------------------------------------


class TestAuthRequired:
    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_get_config_unauthorized(self, unauthed_client):
        """GET /config/get without auth returns 401."""
        response = unauthed_client.get("/api/v1/config/get")
        assert response.status_code == 401

    @patch("module.security.api.DEV_AUTH_BYPASS", False)
    def test_update_config_unauthorized(self, unauthed_client):
        """PATCH /config/update without auth returns 401."""
        response = unauthed_client.patch("/api/v1/config/update", json={})
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /config/get
# ---------------------------------------------------------------------------


class TestGetConfig:
    def test_get_config_success(self, authed_client):
        """GET /config/get returns current configuration."""
        test_config = Config()
        with patch("module.api.config.settings", test_config):
            response = authed_client.get("/api/v1/config/get")

        assert response.status_code == 200
        data = response.json()
        assert "program" in data
        assert "downloader" in data
        assert "rss_parser" in data
        assert data["program"]["rss_time"] == 900
        assert data["program"]["webui_port"] == 7892


# ---------------------------------------------------------------------------
# PATCH /config/update
# ---------------------------------------------------------------------------


class TestUpdateConfig:
    def test_update_config_success(self, authed_client, mock_settings):
        """PATCH /config/update updates configuration successfully."""
        update_data = {
            "program": {
                "rss_time": 600,
                "rename_time": 30,
                "webui_port": 7892,
            },
            "downloader": {
                "type": "qbittorrent",
                "host": "192.168.1.100:8080",
                "username": "admin",
                "password": "newpassword",
                "path": "/downloads/Bangumi",
                "ssl": False,
            },
            "rss_parser": {
                "enable": True,
                "filter": ["720"],
                "language": "zh",
            },
            "bangumi_manage": {
                "enable": True,
                "eps_complete": False,
                "rename_method": "pn",
                "group_tag": False,
                "remove_bad_torrent": False,
            },
            "log": {"debug_enable": True},
            "proxy": {
                "enable": False,
                "type": "http",
                "host": "",
                "port": 0,
                "username": "",
                "password": "",
            },
            "notification": {
                "enable": False,
                "type": "telegram",
                "token": "",
                "chat_id": "",
            },
            "experimental_openai": {
                "enable": False,
                "api_key": "",
                "api_base": "https://api.openai.com/v1",
                "api_type": "openai",
                "api_version": "2023-05-15",
                "model": "gpt-3.5-turbo",
                "deployment_id": "",
            },
        }
        with patch("module.api.config.settings", mock_settings):
            response = authed_client.patch("/api/v1/config/update", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["msg_en"] == "Update config successfully."
        mock_settings.save.assert_called_once()
        mock_settings.load.assert_called_once()

    def test_update_config_failure(self, authed_client, mock_settings):
        """PATCH /config/update handles save failure."""
        mock_settings.save.side_effect = Exception("Save failed")
        update_data = {
            "program": {
                "rss_time": 600,
                "rename_time": 30,
                "webui_port": 7892,
            },
            "downloader": {
                "type": "qbittorrent",
                "host": "192.168.1.100:8080",
                "username": "admin",
                "password": "newpassword",
                "path": "/downloads/Bangumi",
                "ssl": False,
            },
            "rss_parser": {
                "enable": True,
                "filter": ["720"],
                "language": "zh",
            },
            "bangumi_manage": {
                "enable": True,
                "eps_complete": False,
                "rename_method": "pn",
                "group_tag": False,
                "remove_bad_torrent": False,
            },
            "log": {"debug_enable": False},
            "proxy": {
                "enable": False,
                "type": "http",
                "host": "",
                "port": 0,
                "username": "",
                "password": "",
            },
            "notification": {
                "enable": False,
                "type": "telegram",
                "token": "",
                "chat_id": "",
            },
            "experimental_openai": {
                "enable": False,
                "api_key": "",
                "api_base": "https://api.openai.com/v1",
                "api_type": "openai",
                "api_version": "2023-05-15",
                "model": "gpt-3.5-turbo",
                "deployment_id": "",
            },
        }
        with patch("module.api.config.settings", mock_settings):
            response = authed_client.patch("/api/v1/config/update", json=update_data)

        assert response.status_code == 406
        data = response.json()
        assert data["msg_en"] == "Update config failed."

    def test_update_config_partial_validation_error(self, authed_client):
        """PATCH /config/update with invalid data returns 422."""
        # Invalid port (out of range)
        invalid_data = {
            "program": {
                "rss_time": "invalid",  # Should be int
                "rename_time": 60,
                "webui_port": 7892,
            }
        }
        response = authed_client.patch("/api/v1/config/update", json=invalid_data)

        assert response.status_code == 422

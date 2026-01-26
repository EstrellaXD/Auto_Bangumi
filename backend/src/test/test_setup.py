from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from module.api.setup import SENTINEL_PATH, router


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def mock_first_run():
    """Mock conditions for first run: sentinel doesn't exist, config matches defaults."""
    with (
        patch("module.api.setup.SENTINEL_PATH") as mock_sentinel,
        patch("module.api.setup.settings") as mock_settings,
        patch("module.api.setup.Config") as mock_config,
    ):
        mock_sentinel.exists.return_value = False
        mock_settings.dict.return_value = {"test": "default"}
        mock_config.return_value.dict.return_value = {"test": "default"}
        yield


@pytest.fixture
def mock_setup_complete():
    """Mock conditions for setup already complete: sentinel exists."""
    with patch("module.api.setup.SENTINEL_PATH") as mock_sentinel:
        mock_sentinel.exists.return_value = True
        yield


class TestSetupStatus:
    def test_status_first_run(self, client, mock_first_run):
        response = client.get("/api/v1/setup/status")
        assert response.status_code == 200
        data = response.json()
        assert data["need_setup"] is True
        assert "version" in data

    def test_status_setup_complete(self, client, mock_setup_complete):
        response = client.get("/api/v1/setup/status")
        assert response.status_code == 200
        data = response.json()
        assert data["need_setup"] is False

    def test_status_config_changed(self, client):
        """When config differs from defaults, need_setup should be False."""
        with (
            patch("module.api.setup.SENTINEL_PATH") as mock_sentinel,
            patch("module.api.setup.settings") as mock_settings,
            patch("module.api.setup.Config") as mock_config,
            patch("module.api.setup.VERSION", "3.2.0"),  # Non-dev version to test config check
        ):
            mock_sentinel.exists.return_value = False
            mock_settings.dict.return_value = {"test": "changed"}
            mock_config.return_value.dict.return_value = {"test": "default"}
            response = client.get("/api/v1/setup/status")
            assert response.status_code == 200
            data = response.json()
            assert data["need_setup"] is False


class TestSetupGuard:
    def test_test_downloader_blocked_after_setup(self, client, mock_setup_complete):
        response = client.post(
            "/api/v1/setup/test-downloader",
            json={
                "type": "qbittorrent",
                "host": "localhost:8080",
                "username": "admin",
                "password": "admin",
                "ssl": False,
            },
        )
        assert response.status_code == 403

    def test_test_rss_blocked_after_setup(self, client, mock_setup_complete):
        response = client.post(
            "/api/v1/setup/test-rss",
            json={"url": "https://example.com/rss"},
        )
        assert response.status_code == 403

    def test_test_notification_blocked_after_setup(self, client, mock_setup_complete):
        response = client.post(
            "/api/v1/setup/test-notification",
            json={"type": "telegram", "token": "test", "chat_id": "123"},
        )
        assert response.status_code == 403

    def test_complete_blocked_after_setup(self, client, mock_setup_complete):
        response = client.post(
            "/api/v1/setup/complete",
            json={
                "username": "testuser",
                "password": "testpassword123",
                "downloader_type": "qbittorrent",
                "downloader_host": "localhost:8080",
                "downloader_username": "admin",
                "downloader_password": "admin",
                "downloader_path": "/downloads",
                "downloader_ssl": False,
                "rss_url": "",
                "rss_name": "",
                "notification_enable": False,
                "notification_type": "telegram",
                "notification_token": "",
                "notification_chat_id": "",
            },
        )
        assert response.status_code == 403


class TestTestDownloader:
    def test_connection_timeout(self, client, mock_first_run):
        import httpx

        with patch("module.api.setup.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_instance
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                "/api/v1/setup/test-downloader",
                json={
                    "type": "qbittorrent",
                    "host": "localhost:8080",
                    "username": "admin",
                    "password": "admin",
                    "ssl": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_connection_refused(self, client, mock_first_run):
        import httpx

        with patch("module.api.setup.httpx.AsyncClient") as mock_client_cls:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("refused")
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_instance
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                "/api/v1/setup/test-downloader",
                json={
                    "type": "qbittorrent",
                    "host": "localhost:8080",
                    "username": "admin",
                    "password": "admin",
                    "ssl": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestTestRSS:
    def test_invalid_url(self, client, mock_first_run):
        with patch("module.api.setup.RequestContent") as mock_rc:
            mock_instance = AsyncMock()
            mock_instance.get_xml = AsyncMock(return_value=None)
            mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                "/api/v1/setup/test-rss",
                json={"url": "https://invalid.example.com/rss"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestRequestValidation:
    def test_username_too_short(self, client, mock_first_run):
        response = client.post(
            "/api/v1/setup/complete",
            json={
                "username": "ab",
                "password": "testpassword123",
                "downloader_type": "qbittorrent",
                "downloader_host": "localhost:8080",
                "downloader_username": "admin",
                "downloader_password": "admin",
                "downloader_path": "/downloads",
                "downloader_ssl": False,
                "rss_url": "",
                "rss_name": "",
                "notification_enable": False,
                "notification_type": "telegram",
                "notification_token": "",
                "notification_chat_id": "",
            },
        )
        assert response.status_code == 422

    def test_password_too_short(self, client, mock_first_run):
        response = client.post(
            "/api/v1/setup/complete",
            json={
                "username": "testuser",
                "password": "short",
                "downloader_type": "qbittorrent",
                "downloader_host": "localhost:8080",
                "downloader_username": "admin",
                "downloader_password": "admin",
                "downloader_path": "/downloads",
                "downloader_ssl": False,
                "rss_url": "",
                "rss_name": "",
                "notification_enable": False,
                "notification_type": "telegram",
                "notification_token": "",
                "notification_chat_id": "",
            },
        )
        assert response.status_code == 422


class TestSentinelPath:
    def test_sentinel_path_is_in_config_dir(self):
        assert str(SENTINEL_PATH) == "config/.setup_complete"
        assert SENTINEL_PATH.parent == Path("config")

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from module.api.deps import get_context
from module.api.setup import SENTINEL_PATH, router


@pytest.fixture
def mock_ctx():
    """Mock AppContext whose lifecycle methods are awaitable no-ops."""
    ctx = MagicMock()
    ctx.reload_settings = AsyncMock()
    ctx.start_tasks = AsyncMock()
    return ctx


@pytest.fixture
def client(mock_ctx):
    """Create a test client for the FastAPI app."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_context] = lambda: mock_ctx
    yield TestClient(app)
    app.dependency_overrides.clear()


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
            patch(
                "module.api.setup.VERSION", "3.2.0"
            ),  # Non-dev version to test config check
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
    def test_private_ip_accepted(self, client, mock_first_run):
        """Issue #1001: Private IPs must not be rejected for downloader test."""
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
                    "host": "192.168.1.100:8080",
                    "username": "admin",
                    "password": "admin",
                    "ssl": False,
                },
            )
            # Should reach the connection attempt, not get blocked by IP validation
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "connect" in data["message_en"].lower()

    def test_loopback_ip_accepted(self, client, mock_first_run):
        """Issue #1001: Loopback IPs must not be rejected for downloader test."""
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
                    "host": "127.0.0.1:8080",
                    "username": "admin",
                    "password": "admin",
                    "ssl": False,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

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
        with patch("module.api.setup._validate_url"):
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


class TestSetupComplete:
    """Issue: setup wizard must route config reload through AppContext, not
    mutate settings.__dict__ directly (the shared httpx client, notifier, and
    scheduler must be rebuilt after first-run setup)."""

    @staticmethod
    def _payload():
        return {
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
        }

    def test_complete_routes_through_ctx_reload_settings(
        self, client, mock_first_run, mock_ctx
    ):
        """A successful /setup/complete call saves the config and awaits
        ctx.reload_settings(), instead of poking settings.__dict__ directly."""
        from fastapi import HTTPException

        with patch("module.database.Database") as mock_db_cls:
            db_instance = AsyncMock()
            # No admin account yet: _require_default_admin_or_authenticated()
            # treats this as a fresh install and lets setup proceed.
            db_instance.user.get_user = AsyncMock(
                side_effect=HTTPException(status_code=404, detail="not found")
            )
            db_instance.user.update_user = AsyncMock(return_value=True)
            mock_db_cls.return_value.__aenter__ = AsyncMock(return_value=db_instance)
            mock_db_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post("/api/v1/setup/complete", json=self._payload())

        assert response.status_code == 200
        data = response.json()
        assert data["status"] is True
        mock_ctx.reload_settings.assert_awaited_once()
        mock_ctx.start_tasks.assert_awaited_once()


class TestSentinelPath:
    def test_sentinel_path_is_in_config_dir(self):
        assert str(SENTINEL_PATH) == "config/.setup_complete"
        assert SENTINEL_PATH.parent == Path("config")


class TestTestDownloaderHardening:
    """qB 5.2 login compat (#1044) and SSRF hardening (#1041)."""

    @staticmethod
    def _mock_client(get_resp=None, login_resp=None, get_exc=None):
        mock_instance = AsyncMock()
        if get_exc is not None:
            mock_instance.get.side_effect = get_exc
        else:
            mock_instance.get.return_value = get_resp
        mock_instance.post.return_value = login_resp
        cls_patch = patch("module.api.setup.httpx.AsyncClient")
        mock_cls = cls_patch.start()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        return cls_patch

    def _post(self, client, host="192.168.1.100:8080"):
        return client.post(
            "/api/v1/setup/test-downloader",
            json={
                "type": "qbittorrent",
                "host": host,
                "username": "admin",
                "password": "admin",
                "ssl": False,
            },
        )

    def _post_aria2(self, client, host="192.168.1.100:6800", password="secret"):
        return client.post(
            "/api/v1/setup/test-downloader",
            json={
                "type": "aria2",
                "host": host,
                "username": "",
                "password": password,
                "ssl": False,
            },
        )

    def test_aria2_getversion_success(self, client, mock_first_run):
        """aria2 is probed via JSON-RPC getVersion, not the qB login flow."""
        from unittest.mock import MagicMock

        rpc_resp = MagicMock(status_code=200)
        rpc_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "ab-setup",
            "result": {"version": "1.37.0"},
        }
        cls_patch = self._mock_client(login_resp=rpc_resp)
        try:
            response = self._post_aria2(client)
        finally:
            cls_patch.stop()
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_aria2_bad_secret_fails(self, client, mock_first_run):
        """aria2 answering 401 (bad RPC secret) must not be reported as success."""
        from unittest.mock import MagicMock

        rpc_resp = MagicMock(status_code=401)
        rpc_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": "ab-setup",
            "error": {"code": 1, "message": "Unauthorized"},
        }
        cls_patch = self._mock_client(login_resp=rpc_resp)
        try:
            response = self._post_aria2(client)
        finally:
            cls_patch.stop()
        assert response.status_code == 200
        assert response.json()["success"] is False

    def test_login_accepts_204_empty_body(self, client, mock_first_run):
        """qBittorrent >= 5.2 returns 204 + empty body on successful login."""
        from unittest.mock import MagicMock

        get_resp = MagicMock(text="qBittorrent WebUI")
        login_resp = MagicMock(status_code=204, text="")
        cls_patch = self._mock_client(get_resp=get_resp, login_resp=login_resp)
        try:
            response = self._post(client)
        finally:
            cls_patch.stop()
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_login_rejects_200_fails_body(self, client, mock_first_run):
        """200 + 'Fails.' (bad credentials) is still a failure."""
        from unittest.mock import MagicMock

        get_resp = MagicMock(text="qBittorrent WebUI")
        login_resp = MagicMock(status_code=200, text="Fails.")
        cls_patch = self._mock_client(get_resp=get_resp, login_resp=login_resp)
        try:
            response = self._post(client)
        finally:
            cls_patch.stop()
        assert response.status_code == 200
        assert response.json()["success"] is False

    def test_non_http_scheme_rejected(self, client, mock_first_run):
        """Non-http(s) schemes must be rejected before any request is made."""
        response = self._post(client, host="ftp://internal-server:21")
        assert response.status_code == 400

    def test_exception_detail_not_echoed(self, client, mock_first_run):
        """Raw exception text must not leak into the API response (#1041)."""
        cls_patch = self._mock_client(get_exc=Exception("secret-detail-xyz"))
        try:
            response = self._post(client)
        finally:
            cls_patch.stop()
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "secret-detail-xyz" not in data["message_en"]
        assert "secret-detail-xyz" not in data["message_zh"]

    def test_login_rejects_200_html_body(self, client, mock_first_run):
        """A proxy answering 200 + HTML to the login POST is not a success."""
        from unittest.mock import MagicMock

        get_resp = MagicMock(text="qBittorrent WebUI")
        login_resp = MagicMock(status_code=200, text="<html><body>portal</body></html>")
        cls_patch = self._mock_client(get_resp=get_resp, login_resp=login_resp)
        try:
            response = self._post(client)
        finally:
            cls_patch.stop()
        assert response.status_code == 200
        assert response.json()["success"] is False

"""Tests for Config API endpoints and config sanitization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.api.config import _restore_masked, _sanitize_dict
from module.api.deps import get_context
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
def mock_ctx():
    """Mock AppContext whose reload_settings is an awaitable no-op."""
    ctx = MagicMock()
    ctx.reload_settings = AsyncMock()
    return ctx


@pytest.fixture
def authed_client(app, mock_ctx):
    """TestClient with auth and context dependencies overridden."""

    async def mock_user():
        return "testuser"

    app.dependency_overrides[get_current_user] = mock_user
    app.dependency_overrides[get_context] = lambda: mock_ctx
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
    settings.llm = MagicMock()
    settings.llm.enable = False
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
    def test_update_config_success(self, authed_client, mock_settings, mock_ctx):
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
        # settings.load() now runs inside ctx.reload_settings(), which the route
        # awaits after saving.
        mock_ctx.reload_settings.assert_awaited_once()

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


# ---------------------------------------------------------------------------
# _sanitize_dict unit tests
# ---------------------------------------------------------------------------


class TestSanitizeDict:
    def test_masks_password_key(self):
        """Keys containing 'password' are masked."""
        result = _sanitize_dict({"password": "secret"})
        assert result["password"] == "********"

    def test_masks_api_key(self):
        """Keys containing 'api_key' are masked."""
        result = _sanitize_dict({"api_key": "sk-abc123"})
        assert result["api_key"] == "********"

    def test_masks_token_key(self):
        """Keys containing 'token' are masked."""
        result = _sanitize_dict({"token": "bearer-xyz"})
        assert result["token"] == "********"

    def test_masks_secret_key(self):
        """Keys containing 'secret' are masked."""
        result = _sanitize_dict({"my_secret": "topsecret"})
        assert result["my_secret"] == "********"

    def test_case_insensitive_key_matching(self):
        """Sensitive key matching is case-insensitive."""
        result = _sanitize_dict({"API_KEY": "abc"})
        assert result["API_KEY"] == "********"

    def test_non_sensitive_keys_pass_through(self):
        """Non-sensitive keys are returned unchanged."""
        result = _sanitize_dict({"host": "localhost", "port": 8080, "enable": True})
        assert result["host"] == "localhost"
        assert result["port"] == 8080
        assert result["enable"] is True

    def test_nested_dict_recursed(self):
        """Nested dicts are processed recursively."""
        result = _sanitize_dict(
            {
                "downloader": {
                    "host": "localhost",
                    "password": "secret",
                }
            }
        )
        assert result["downloader"]["host"] == "localhost"
        assert result["downloader"]["password"] == "********"

    def test_deeply_nested_dict(self):
        """Deeply nested sensitive keys are masked."""
        result = _sanitize_dict({"level1": {"level2": {"api_key": "deep-secret"}}})
        assert result["level1"]["level2"]["api_key"] == "********"

    def test_non_string_value_not_masked(self):
        """Non-string values with sensitive-looking keys are NOT masked."""
        result = _sanitize_dict({"password": 12345})
        # Only string values are masked; integers pass through
        assert result["password"] == 12345

    def test_empty_dict(self):
        """Empty dict returns empty dict."""
        assert _sanitize_dict({}) == {}

    def test_mixed_sensitive_and_plain(self):
        """Mix of sensitive and plain keys handled correctly."""
        result = _sanitize_dict(
            {
                "username": "admin",
                "password": "secret",
                "host": "10.0.0.1",
                "token": "jwt-abc",
            }
        )
        assert result["username"] == "admin"
        assert result["host"] == "10.0.0.1"
        assert result["password"] == "********"
        assert result["token"] == "********"

    def test_sanitize_list_of_dicts(self):
        """Lists containing dicts are recursed into."""
        result = _sanitize_dict(
            {
                "providers": [
                    {"type": "telegram", "token": "secret-token"},
                    {"type": "bark", "token": "another-secret"},
                ]
            }
        )
        assert result["providers"][0]["token"] == "********"
        assert result["providers"][1]["token"] == "********"
        assert result["providers"][0]["type"] == "telegram"

    def test_get_config_masks_sensitive_fields(self, authed_client):
        """GET /config/get response masks password and api_key fields."""
        test_config = Config()
        with patch("module.api.config.settings", test_config):
            response = authed_client.get("/api/v1/config/get")
        assert response.status_code == 200
        data = response.json()
        # Downloader password should be masked
        assert data["downloader"]["password"] == "********"
        # LLM api_key should be masked (it's an empty string but still masked)
        assert data["llm"]["api_key"] == "********"
        # Legacy OpenAI api_key should be masked too
        assert data["experimental_openai"]["api_key"] == "********"


# ---------------------------------------------------------------------------
# _restore_masked unit tests (#995)
# ---------------------------------------------------------------------------


class TestRestoreMasked:
    """Issue #995: Masked passwords must not overwrite real credentials."""

    def test_masked_password_restored(self):
        """Masked password is replaced with the real stored value."""
        incoming = {"password": "********"}
        current = {"password": "real_secret"}
        _restore_masked(incoming, current)
        assert incoming["password"] == "real_secret"

    def test_new_password_preserved(self):
        """Non-masked password value is kept as-is."""
        incoming = {"password": "new_password"}
        current = {"password": "old_password"}
        _restore_masked(incoming, current)
        assert incoming["password"] == "new_password"

    def test_nested_masked_password_restored(self):
        """Masked password inside nested dict is restored."""
        incoming = {"downloader": {"host": "10.0.0.1", "password": "********"}}
        current = {"downloader": {"host": "10.0.0.1", "password": "adminadmin"}}
        _restore_masked(incoming, current)
        assert incoming["downloader"]["password"] == "adminadmin"

    def test_nested_new_password_preserved(self):
        """Non-masked password inside nested dict is kept."""
        incoming = {"downloader": {"password": "changed"}}
        current = {"downloader": {"password": "old"}}
        _restore_masked(incoming, current)
        assert incoming["downloader"]["password"] == "changed"

    def test_multiple_sensitive_fields(self):
        """All sensitive fields are handled independently."""
        incoming = {
            "downloader": {"password": "********"},
            "proxy": {"password": "new_proxy_pass"},
            "experimental_openai": {"api_key": "********"},
        }
        current = {
            "downloader": {"password": "qb_pass"},
            "proxy": {"password": "old_proxy_pass"},
            "experimental_openai": {"api_key": "sk-real-key"},
        }
        _restore_masked(incoming, current)
        assert incoming["downloader"]["password"] == "qb_pass"
        assert incoming["proxy"]["password"] == "new_proxy_pass"
        assert incoming["experimental_openai"]["api_key"] == "sk-real-key"

    def test_non_sensitive_mask_value_untouched(self):
        """A non-sensitive key with '********' value is not modified."""
        incoming = {"host": "********"}
        current = {"host": "10.0.0.1"}
        _restore_masked(incoming, current)
        assert incoming["host"] == "********"

    def test_list_of_dicts_restored(self):
        """Masked tokens inside list items are restored."""
        incoming = {
            "providers": [
                {"type": "telegram", "token": "********"},
                {"type": "bark", "token": "new-bark-token"},
            ]
        }
        current = {
            "providers": [
                {"type": "telegram", "token": "real-tg-token"},
                {"type": "bark", "token": "old-bark-token"},
            ]
        }
        _restore_masked(incoming, current)
        assert incoming["providers"][0]["token"] == "real-tg-token"
        assert incoming["providers"][1]["token"] == "new-bark-token"

    def test_empty_dicts(self):
        """Empty dicts don't cause errors."""
        _restore_masked({}, {})

    def test_round_trip_preserves_credentials(self):
        """Full round-trip: sanitize then restore recovers original values."""
        original = {
            "downloader": {"host": "10.0.0.1", "password": "secret123"},
            "llm": {"api_key": "sk-abc", "model": "gpt-4o-mini"},
        }
        sanitized = _sanitize_dict(original)
        assert sanitized["downloader"]["password"] == "********"
        assert sanitized["llm"]["api_key"] == "********"

        _restore_masked(sanitized, original)
        assert sanitized["downloader"]["password"] == "secret123"
        assert sanitized["llm"]["api_key"] == "sk-abc"
        assert sanitized["downloader"]["host"] == "10.0.0.1"
        assert sanitized["llm"]["model"] == "gpt-4o-mini"

    def test_list_item_deleted_restores_survivor_from_own_entry(self):
        """删除列表首项后，幸存项的掩码密钥必须从它自己的旧值恢复，
        不能按下标错拿被删项的密钥。"""
        incoming = {
            "providers": [
                {"type": "telegram", "chat_id": "2", "token": "********"},
            ]
        }
        current = {
            "providers": [
                {"type": "telegram", "chat_id": "1", "token": "tg-first"},
                {"type": "telegram", "chat_id": "2", "token": "tg-second"},
            ]
        }
        _restore_masked(incoming, current)
        assert incoming["providers"][0]["token"] == "tg-second"

    def test_list_reordered_restores_each_from_matching_entry(self):
        """列表重排后，每个掩码项按自身身份（非敏感字段）匹配恢复。"""
        incoming = {
            "providers": [
                {"type": "bark", "chat_id": "b", "token": "********"},
                {"type": "telegram", "chat_id": "a", "token": "********"},
            ]
        }
        current = {
            "providers": [
                {"type": "telegram", "chat_id": "a", "token": "tg-token"},
                {"type": "bark", "chat_id": "b", "token": "bark-token"},
            ]
        }
        _restore_masked(incoming, current)
        assert incoming["providers"][0]["token"] == "bark-token"
        assert incoming["providers"][1]["token"] == "tg-token"

    def test_list_same_length_edited_fields_falls_back_to_index(self):
        """长度不变时编辑了非敏感字段（无法按身份匹配）→ 按下标恢复，
        保持旧行为：改 chat_id 不应要求重输 token。"""
        incoming = {
            "providers": [
                {"type": "telegram", "chat_id": "changed", "token": "********"},
            ]
        }
        current = {
            "providers": [
                {"type": "telegram", "chat_id": "orig", "token": "tg-token"},
            ]
        }
        _restore_masked(incoming, current)
        assert incoming["providers"][0]["token"] == "tg-token"

    def test_list_structural_change_plus_edit_raises(self):
        """删项 + 同时编辑幸存项的身份字段 → 无法可靠匹配，必须报错
        而不是猜错来源静默写坏密钥。"""
        from module.api.config import MaskRestoreError

        incoming = {
            "providers": [
                {"type": "telegram", "chat_id": "edited", "token": "********"},
            ]
        }
        current = {
            "providers": [
                {"type": "telegram", "chat_id": "1", "token": "tg-first"},
                {"type": "telegram", "chat_id": "2", "token": "tg-second"},
            ]
        }
        with pytest.raises(MaskRestoreError):
            _restore_masked(incoming, current)

    def test_list_item_deleted_among_identical_identities_raises(self):
        """两个身份完全相同（只差密钥）的项删掉一个：无法知道幸存的是哪个，
        必须报错而不是按下标把被删项的密钥塞给幸存者。"""
        from module.api.config import MaskRestoreError

        incoming = {
            "providers": [
                {"type": "telegram", "chat_id": "same", "token": "********"},
            ]
        }
        current = {
            "providers": [
                {"type": "telegram", "chat_id": "same", "token": "tg-first"},
                {"type": "telegram", "chat_id": "same", "token": "tg-second"},
            ]
        }
        with pytest.raises(MaskRestoreError):
            _restore_masked(incoming, current)

    def test_list_item_added_with_new_secret_passes(self):
        """新增列表项带明文新密钥：无掩码,不需要匹配,不得报错。"""
        incoming = {
            "providers": [
                {"type": "telegram", "chat_id": "1", "token": "********"},
                {"type": "bark", "chat_id": "b", "token": "new-bark-token"},
            ]
        }
        current = {
            "providers": [
                {"type": "telegram", "chat_id": "1", "token": "tg-token"},
            ]
        }
        _restore_masked(incoming, current)
        assert incoming["providers"][0]["token"] == "tg-token"
        assert incoming["providers"][1]["token"] == "new-bark-token"

    def test_update_config_preserves_password_when_masked(
        self, authed_client, mock_settings
    ):
        """PATCH /config/update must not overwrite a real password with '********'."""
        mock_settings.dict.return_value = {
            "program": {"rss_time": 900, "rename_time": 60, "webui_port": 7892},
            "downloader": {
                "type": "qbittorrent",
                "host": "192.168.1.1:8080",
                "username": "admin",
                "password": "realpassword",
                "path": "/downloads",
                "ssl": True,
            },
            "rss_parser": {"enable": True, "filter": [], "language": "zh"},
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
        payload = {
            "program": {"rss_time": 900, "rename_time": 60, "webui_port": 7892},
            "downloader": {
                "type": "qbittorrent",
                "host": "192.168.1.1:8080",
                "username": "admin",
                "password": "********",
                "path": "/downloads",
                "ssl": False,
            },
            "rss_parser": {"enable": True, "filter": [], "language": "zh"},
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
            response = authed_client.patch("/api/v1/config/update", json=payload)

        assert response.status_code == 200
        saved = mock_settings.save.call_args[1]["config_dict"]
        assert saved["downloader"]["password"] == "realpassword"
        assert saved["downloader"]["ssl"] is False


class TestListLLMModels:
    def _mock_parser(self, models=None, error=None):
        parser = MagicMock()
        if error is not None:
            parser.list_models = AsyncMock(side_effect=error)
        else:
            parser.list_models = AsyncMock(return_value=models or [])
        parser.aclose = AsyncMock()
        return parser

    def test_returns_models_from_provider(self, authed_client):
        parser = self._mock_parser(models=["gpt-5", "gpt-5-mini"])
        with patch("module.api.config.LLMParser", return_value=parser) as cls:
            response = authed_client.post(
                "/api/v1/config/llm/models",
                json={"provider": "openai", "api_key": "sk-x", "base_url": ""},
            )
        assert response.status_code == 200
        assert response.json()["models"] == ["gpt-5", "gpt-5-mini"]
        cls.assert_called_once_with(
            api_key="sk-x", provider="openai", base_url="", timeout=10.0
        )
        parser.aclose.assert_awaited_once()

    def test_masked_key_falls_back_to_saved_key(self, authed_client):
        parser = self._mock_parser(models=["m"])
        saved = MagicMock()
        # 掩码回退现在按提供商取值（providers[id] 覆盖 → 扁平字段兜底）
        saved.llm.effective.return_value = ("sk-saved", "", "")
        with (
            patch("module.api.config.settings", saved),
            patch("module.api.config.LLMParser", return_value=parser) as cls,
        ):
            response = authed_client.post(
                "/api/v1/config/llm/models",
                json={"provider": "anthropic", "api_key": "********"},
            )
        assert response.status_code == 200
        assert cls.call_args.kwargs["api_key"] == "sk-saved"

    def test_missing_key_returns_400(self, authed_client):
        saved = MagicMock()
        saved.llm.effective.return_value = ("", "", "")
        with patch("module.api.config.settings", saved):
            response = authed_client.post(
                "/api/v1/config/llm/models",
                json={"provider": "openai", "api_key": ""},
            )
        assert response.status_code == 400

    def test_provider_error_returns_502_and_closes(self, authed_client):
        parser = self._mock_parser(error=RuntimeError("boom"))
        with patch("module.api.config.LLMParser", return_value=parser):
            response = authed_client.post(
                "/api/v1/config/llm/models",
                json={"provider": "gemini", "api_key": "g-key"},
            )
        assert response.status_code == 502
        assert "boom" not in response.text
        parser.aclose.assert_awaited_once()

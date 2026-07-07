"""LLM 提供商/认证 API：/config/llm/providers + auth begin/complete/status/disconnect。"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api import v1
from module.parser.analyser.providers.base import (
    AuthChallenge,
    LLMProviderAdapter,
    ProviderInfo,
    TokenSet,
)
from module.security.api import get_current_user


class FakeDeviceAdapter(LLMProviderAdapter):
    info = ProviderInfo(
        id="fake-device",
        display_name="Fake Device",
        auth_kind="device_code",
        builtin=False,
    )

    async def parse(self, raw):
        return None

    async def list_models(self):
        return []

    async def begin_auth(self) -> AuthChallenge:
        return AuthChallenge(
            method="device_code",
            user_code="WXYZ-1234",
            verification_uri="https://example.com/device",
            state="state-123",
        )

    async def complete_auth(self, state, user_input=""):
        return TokenSet(access_token="at", account_label="tester@example.com")

    async def revoke(self, tokens):
        return None


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(v1, prefix="/api")
    app.state.ctx = MagicMock()
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


@pytest.fixture(autouse=True)
def _clear_pending():
    from module.api import llm as llm_api

    llm_api._PENDING.clear()
    yield
    for task in list(llm_api._POLL_TASKS):
        task.cancel()
    llm_api._POLL_TASKS.clear()
    llm_api._PENDING.clear()


@patch("module.security.api.DEV_AUTH_BYPASS", False)
def test_providers_requires_auth(unauthed_client):
    assert unauthed_client.get("/api/v1/config/llm/providers").status_code == 401


def test_list_providers_includes_builtins_and_presets(authed_client):
    # 全为 api_key 提供商（无插件安装）→ 不触碰 DB
    resp = authed_client.get("/api/v1/config/llm/providers")
    assert resp.status_code == 200
    ids = {p["id"] for p in resp.json()["providers"]}
    assert {"openai", "anthropic", "gemini", "kimi", "deepseek"} <= ids


def test_auth_begin_returns_opaque_handle_and_hides_device_code(authed_client):
    from module.api import llm as llm_api

    async def _noop(*args, **kwargs):
        return None

    with (
        patch.object(llm_api.registry, "resolve", return_value=FakeDeviceAdapter),
        # 让后台轮询任务空转，避免它在断言前清掉 pending
        patch("module.api.llm._device_poll_loop", new=_noop),
    ):
        resp = authed_client.post("/api/v1/config/llm/providers/fake-device/auth/begin")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_code"] == "WXYZ-1234"
    assert body["method"] == "device_code"
    # 返回的是不透明 handle，绝非适配器原始 state（device_code 藏服务端 blob）
    handle = body["state"]
    assert handle and handle != "state-123"
    assert "state-123" not in json.dumps(body)
    pending = llm_api._PENDING[handle]
    assert pending.provider_id == "fake-device"
    assert pending.blob == "state-123"  # 敏感态只在服务端


def test_auth_complete_saves_credential(authed_client):
    from module.api import llm as llm_api
    from module.api.llm import PendingAuth

    llm_api._PENDING["handle-1"] = PendingAuth(
        provider_id="fake-device", created=0.0, expires=9e18, blob="blob-secret"
    )
    save = AsyncMock()
    with (
        patch.object(llm_api.registry, "resolve", return_value=FakeDeviceAdapter),
        patch("module.api.llm.CredentialStore") as store_cls,
    ):
        store_cls.return_value.save = save
        resp = authed_client.post(
            "/api/v1/config/llm/providers/fake-device/auth/complete",
            json={"state": "handle-1", "code": ""},
        )
    assert resp.status_code == 200
    assert resp.json()["connected"] is True
    assert resp.json()["account_label"] == "tester@example.com"
    save.assert_awaited_once()
    assert "handle-1" not in llm_api._PENDING  # 用完即清


async def test_device_poll_loop_saves_on_success():
    """服务端轮询：complete_auth 成功即写库 + bump generation + 清 pending。"""
    from module.api import llm as llm_api
    from module.api.llm import PendingAuth

    llm_api._PENDING["h"] = PendingAuth(
        provider_id="fake-device",
        created=0.0,
        expires=9e18,
        blob=json.dumps({"device_code": "DC", "interval": 1}),
    )
    save = AsyncMock()
    try:
        with (
            patch.object(llm_api.registry, "resolve", return_value=FakeDeviceAdapter),
            patch("module.api.llm.CredentialStore") as store_cls,
            patch("module.api.llm.bump_auth_generation") as bump,
            patch("module.api.llm.asyncio.sleep", new_callable=AsyncMock),
        ):
            store_cls.return_value.save = save
            await llm_api._device_poll_loop("fake-device", "h", expires_in=900)

        save.assert_awaited_once()
        bump.assert_called_once_with("fake-device")
        assert "h" not in llm_api._PENDING
    finally:
        llm_api._PENDING.pop("h", None)


def test_auth_complete_unknown_state_returns_400(authed_client):
    resp = authed_client.post(
        "/api/v1/config/llm/providers/fake-device/auth/complete",
        json={"state": "nope", "code": ""},
    )
    assert resp.status_code == 400


def test_auth_status_reports_connected(authed_client):
    with patch("module.api.llm.CredentialStore") as store_cls:
        store_cls.return_value.load = AsyncMock(
            return_value=TokenSet(access_token="at", account_label="me@x.com")
        )
        resp = authed_client.get("/api/v1/config/llm/providers/fake-device/auth/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["account_label"] == "me@x.com"
    assert "access_token" not in body  # token 绝不下发


def test_install_success(authed_client):
    from module.llm_plugins import InstallResult

    installer = MagicMock()
    installer.install = AsyncMock(
        return_value=InstallResult(success=True, version="1.0.0")
    )
    with patch("module.llm_plugins.PluginInstaller", return_value=installer):
        resp = authed_client.post("/api/v1/config/llm/providers/fake-copilot/install")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.0.0"


def test_install_failure_returns_400_and_notifies(authed_client, app):
    from module.llm_plugins import InstallResult
    from module.notification import LLMPluginInstallFailedEvent

    app.state.ctx.notifier.send_event = AsyncMock()
    installer = MagicMock()
    installer.install = AsyncMock(
        return_value=InstallResult(success=False, message="Plugin signature invalid")
    )
    with patch("module.llm_plugins.PluginInstaller", return_value=installer):
        resp = authed_client.post("/api/v1/config/llm/providers/fake-copilot/install")
    assert resp.status_code == 400
    event = app.state.ctx.notifier.send_event.await_args.args[0]
    assert isinstance(event, LLMPluginInstallFailedEvent)
    assert event.plugin_id == "fake-copilot"


def test_uninstall_builtin_returns_400(authed_client):
    from module.llm_plugins import InstallResult

    installer = MagicMock()
    installer.uninstall = AsyncMock(
        return_value=InstallResult(
            success=False, message="openai is a builtin provider"
        )
    )
    with patch("module.llm_plugins.PluginInstaller", return_value=installer):
        resp = authed_client.delete("/api/v1/config/llm/providers/openai")
    assert resp.status_code == 400


def test_disconnect_clears_and_bumps_generation(authed_client):
    from module.api import llm as llm_api

    clear = AsyncMock()
    with (
        patch.object(llm_api.registry, "resolve", return_value=FakeDeviceAdapter),
        patch("module.api.llm.CredentialStore") as store_cls,
        patch("module.api.llm.bump_auth_generation") as bump,
    ):
        store_cls.return_value.clear = clear
        store_cls.return_value.load = AsyncMock(return_value=TokenSet(access_token="a"))
        resp = authed_client.delete("/api/v1/config/llm/providers/fake-device/auth")
    assert resp.status_code == 200
    clear.assert_awaited_once()
    bump.assert_called_once_with("fake-device")

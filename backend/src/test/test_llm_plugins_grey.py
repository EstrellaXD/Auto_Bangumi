"""M6 灰色插件（github-copilot / codex-chatgpt）：装载 + device flow + parse。

从 ``plugins/<id>/`` 真实源码打包 zip → 用测试密钥签名 → 走安装管线装载真实
适配器 → 用 MockTransport 模拟各家 HTTP 端点，验证 begin/complete/parse。
"""

import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from module.llm_plugins.installer import PluginInstaller
from module.parser.analyser.providers.base import AdapterContext, AuthExpiredError

PLUGINS_SRC = Path(__file__).resolve().parents[3] / "plugins"


@pytest.fixture
def keypair(tmp_path):
    priv = Ed25519PrivateKey.generate()
    pubkey_path = tmp_path / "pub.pem"
    pubkey_path.write_bytes(
        priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    return priv, pubkey_path


def _zip_plugin(plugin_id: str) -> bytes:
    src = PLUGINS_SRC / plugin_id
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, path.relative_to(src).as_posix())
    return buf.getvalue()


async def _install(tmp_path, keypair, plugin_id):
    priv, pubkey_path = keypair
    zip_bytes = _zip_plugin(plugin_id)
    manifest = json.loads((PLUGINS_SRC / plugin_id / "plugin.json").read_text())
    catalog = {
        "schema": 1,
        "plugins": [
            {
                "id": plugin_id,
                "name": manifest["name"],
                "version": manifest["version"],
                "min_ab_version": manifest["min_ab_version"],
                "auth_kind": manifest["auth_kind"],
                "asset": f"{plugin_id}-{manifest['version']}.zip",
                "sha256": hashlib.sha256(zip_bytes).hexdigest(),
            }
        ],
    }
    catalog_bytes = json.dumps(catalog).encode()

    def handler(request):
        url = str(request.url)
        if url.endswith("catalog.json"):
            return httpx.Response(200, content=catalog_bytes)
        if url.endswith("catalog.json.sig"):
            return httpx.Response(
                200, text=base64.b64encode(priv.sign(catalog_bytes)).decode()
            )
        if url.endswith(".zip"):
            return httpx.Response(200, content=zip_bytes)
        if url.endswith(".zip.sig"):
            return httpx.Response(
                200, text=base64.b64encode(priv.sign(zip_bytes)).decode()
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    installer = PluginInstaller(
        root=tmp_path / "plugins",
        pubkey_path=pubkey_path,
        client=client,
        app_version="3.3.0",
    )
    result = await installer.install(plugin_id)
    assert result.success, result.message
    return installer


def _ctx(handler, credentials=None, model=""):
    """构造注入 MockTransport-http-client 的 AdapterContext。"""

    def build_client(_timeout):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    return AdapterContext(
        model=model,
        build_http_client=build_client,
        credentials=credentials or AsyncMock(),
    )


# ---------------------------------------------------------------------------
# github-copilot
# ---------------------------------------------------------------------------


class TestGithubCopilot:
    async def test_install_and_resolve(self, tmp_path, keypair):
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "github-copilot")
        cls = registry.resolve("github-copilot")
        assert cls.info.id == "github-copilot"
        assert cls.info.auth_kind == "device_code"
        registry.invalidate()

    async def test_begin_auth_returns_user_code(self, tmp_path, keypair):
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "github-copilot")
        cls = registry.resolve("github-copilot")

        def handler(request):
            assert "login/device/code" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "device_code": "DC-secret",
                    "user_code": "WXYZ-1234",
                    "verification_uri": "https://github.com/login/device",
                    "interval": 5,
                    "expires_in": 900,
                },
            )

        adapter = cls(_ctx(handler))
        challenge = await adapter.begin_auth()
        assert challenge.user_code == "WXYZ-1234"
        assert challenge.method == "device_code"
        # device_code 藏在 state 里（不作为 user_code 下发）
        assert "DC-secret" in challenge.state
        assert "DC-secret" != challenge.user_code
        await adapter.aclose()
        registry.invalidate()

    async def test_complete_auth_pending_raises(self, tmp_path, keypair):
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "github-copilot")
        cls = registry.resolve("github-copilot")

        def handler(request):
            return httpx.Response(200, json={"error": "authorization_pending"})

        adapter = cls(_ctx(handler))
        with pytest.raises(AuthExpiredError):
            await adapter.complete_auth(json.dumps({"device_code": "DC"}))
        await adapter.aclose()
        registry.invalidate()

    async def test_parse_uses_tool_call_and_copilot_token(self, tmp_path, keypair):
        from module.parser.analyser.providers.base import TokenSet
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "github-copilot")
        cls = registry.resolve("github-copilot")

        episode = {
            "title_en": "Test",
            "title_zh": None,
            "title_jp": None,
            "season": 1,
            "season_raw": "",
            "episode": 5,
            "sub": "CHS",
            "group": "G",
            "resolution": "1080p",
            "source": "Web",
        }
        seen = {"copilot_token_fetched": False, "editor_header": False}

        def handler(request):
            url = str(request.url)
            if "copilot_internal/v2/token" in url:
                seen["copilot_token_fetched"] = True
                assert request.headers["authorization"].startswith("token ghu_")
                return httpx.Response(
                    200, json={"token": "cop_tok", "expires_at": 9e18}
                )
            if "chat/completions" in url:
                seen["editor_header"] = "editor-version" in request.headers
                assert request.headers["authorization"] == "Bearer cop_tok"
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {
                                "message": {
                                    "tool_calls": [
                                        {"function": {"arguments": json.dumps(episode)}}
                                    ]
                                }
                            }
                        ]
                    },
                )
            return httpx.Response(404)

        creds = AsyncMock()
        creds.load = AsyncMock(return_value=TokenSet(access_token="ghu_abc"))
        adapter = cls(_ctx(handler, credentials=creds))
        result = await adapter.parse("[G] Test - 05 [1080p]")
        assert result == episode
        assert seen["copilot_token_fetched"] is True
        assert seen["editor_header"] is True
        await adapter.aclose()
        registry.invalidate()

    async def test_parse_without_credentials_raises(self, tmp_path, keypair):
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "github-copilot")
        cls = registry.resolve("github-copilot")
        creds = AsyncMock()
        creds.load = AsyncMock(return_value=None)
        adapter = cls(_ctx(lambda r: httpx.Response(404), credentials=creds))
        with pytest.raises(AuthExpiredError):
            await adapter.parse("raw")
        await adapter.aclose()
        registry.invalidate()


# ---------------------------------------------------------------------------
# codex-chatgpt
# ---------------------------------------------------------------------------


class TestCodexChatgpt:
    async def test_install_and_resolve(self, tmp_path, keypair):
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "codex-chatgpt")
        cls = registry.resolve("codex-chatgpt")
        assert cls.info.id == "codex-chatgpt"
        registry.invalidate()

    async def test_complete_auth_decodes_account_id(self, tmp_path, keypair):
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "codex-chatgpt")
        cls = registry.resolve("codex-chatgpt")

        # 构造带 chatgpt_account_id claim 的假 JWT
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        claims = (
            base64.urlsafe_b64encode(
                json.dumps({"chatgpt_account_id": "acc-42"}).encode()
            )
            .decode()
            .rstrip("=")
        )
        fake_jwt = f"{header}.{claims}.sig"

        def handler(request):
            return httpx.Response(
                200,
                json={
                    "access_token": fake_jwt,
                    "refresh_token": "rt-1",
                    "expires_in": 3600,
                },
            )

        adapter = cls(_ctx(handler))
        tokens = await adapter.complete_auth(json.dumps({"device_code": "DC"}))
        assert tokens.access_token == fake_jwt
        assert tokens.extra["account_id"] == "acc-42"
        assert tokens.refresh_token == "rt-1"
        await adapter.aclose()
        registry.invalidate()

    async def test_parse_sends_originator_and_account_headers(self, tmp_path, keypair):
        from module.parser.analyser.providers.base import TokenSet
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "codex-chatgpt")
        cls = registry.resolve("codex-chatgpt")

        episode = {
            "title_en": "X",
            "title_zh": None,
            "title_jp": None,
            "season": 1,
            "season_raw": "",
            "episode": 1,
            "sub": "",
            "group": "",
            "resolution": "",
            "source": "",
        }
        seen = {}

        def handler(request):
            seen["originator"] = request.headers.get("originator")
            seen["account"] = request.headers.get("chatgpt-account-id")
            return httpx.Response(
                200,
                json={"output": [{"content": [{"text": json.dumps(episode)}]}]},
            )

        creds = AsyncMock()
        creds.load = AsyncMock(
            return_value=TokenSet(
                access_token="at", expires_at=9e18, extra={"account_id": "acc-42"}
            )
        )
        adapter = cls(_ctx(handler, credentials=creds))
        result = await adapter.parse("raw title")
        assert result == episode
        assert seen["originator"] == "codex_cli_rs"
        assert seen["account"] == "acc-42"
        await adapter.aclose()
        registry.invalidate()

    async def test_expired_token_triggers_refresh(self, tmp_path, keypair):
        from module.parser.analyser.providers.base import TokenSet
        from module.parser.analyser.providers.registry import registry

        await _install(tmp_path, keypair, "codex-chatgpt")
        cls = registry.resolve("codex-chatgpt")
        refreshed_saved: dict = {}

        def handler(request):
            url = str(request.url)
            if url.endswith("oauth/token"):
                return httpx.Response(
                    200, json={"access_token": "new-at", "expires_in": 3600}
                )
            return httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "text": json.dumps(
                                        {
                                            "title_en": None,
                                            "title_zh": None,
                                            "title_jp": None,
                                            "season": 1,
                                            "season_raw": "",
                                            "episode": 1,
                                            "sub": "",
                                            "group": "",
                                            "resolution": "",
                                            "source": "",
                                        }
                                    )
                                }
                            ]
                        }
                    ]
                },
            )

        creds = AsyncMock()
        creds.load = AsyncMock(
            return_value=TokenSet(
                access_token="old", refresh_token="rt", expires_at=0.0
            )
        )
        creds.save = AsyncMock(
            side_effect=lambda t: refreshed_saved.update(at=t.access_token)
        )
        adapter = cls(_ctx(handler, credentials=creds))
        await adapter.parse("raw")
        # 过期 → 刷新 → 保存新 token
        assert refreshed_saved.get("at") == "new-at"
        await adapter.aclose()
        registry.invalidate()

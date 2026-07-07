"""LLM 插件安装管线：签名下载 → 校验 → 解包 → 加载 → 解析（克隆 updater 模式）。

用测试 ed25519 密钥对 + 内存构造的假插件 zip + httpx.MockTransport + tmp_path，
覆盖安全路径：sha 不符、无签名、坏签名、zip-slip、版本不兼容、id 不匹配全部拒绝。
"""

import base64
import hashlib
import io
import json
import zipfile

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from module.llm_plugins.installer import PluginInstaller

PLUGIN_ID = "fake-copilot"
VERSION = "1.0.0"

ADAPTER_SOURCE = """
from module.parser.analyser.providers.base import (
    LLMProviderAdapter, ProviderInfo,
)


class FakeCopilotAdapter(LLMProviderAdapter):
    info = ProviderInfo(
        id="fake-copilot",
        display_name="Fake Copilot",
        auth_kind="device_code",
        builtin=False,
    )

    async def parse(self, raw):
        return {"title_en": "ok", "title_zh": None, "title_jp": None,
                "season": 1, "season_raw": "", "episode": 1,
                "sub": "", "group": "", "resolution": "", "source": ""}

    async def list_models(self):
        return ["fake-model"]
"""


@pytest.fixture
def keypair(tmp_path):
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pubkey_path = tmp_path / "pub.pem"
    pubkey_path.write_bytes(
        pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    return priv, pubkey_path


def _make_plugin_zip(
    manifest_extra: dict | None = None, member_name: str | None = None
) -> bytes:
    manifest = {
        "schema": 1,
        "id": PLUGIN_ID,
        "name": "Fake Copilot",
        "version": VERSION,
        "min_ab_version": "3.3.0",
        "entry": "ab_fake_copilot.adapter:FakeCopilotAdapter",
        "auth_kind": "device_code",
    }
    manifest.update(manifest_extra or {})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("plugin.json", json.dumps(manifest))
        adapter_path = member_name or "ab_fake_copilot/adapter.py"
        zf.writestr(adapter_path, ADAPTER_SOURCE)
        if member_name is None:
            zf.writestr("ab_fake_copilot/__init__.py", "")
    return buf.getvalue()


def _catalog(zip_bytes: bytes, priv, extra: dict | None = None) -> dict:
    entry = {
        "schema": 1,
        "id": PLUGIN_ID,
        "name": "Fake Copilot",
        "version": VERSION,
        "min_ab_version": "3.3.0",
        "auth_kind": "device_code",
        "asset": f"{PLUGIN_ID}-{VERSION}.zip",
        "sha256": hashlib.sha256(zip_bytes).hexdigest(),
    }
    entry.update(extra or {})
    return {"schema": 1, "plugins": [entry]}


def _sign(priv, data: bytes) -> str:
    return base64.b64encode(priv.sign(data)).decode()


def _installer(tmp_path, keypair, zip_bytes, *, catalog=None, tamper_sig=False):
    priv, pubkey_path = keypair
    catalog = catalog if catalog is not None else _catalog(zip_bytes, priv)
    catalog_bytes = json.dumps(catalog).encode()
    sig = _sign(priv, zip_bytes)
    if tamper_sig:
        sig = base64.b64encode(b"\x00" * 64).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("catalog.json"):
            return httpx.Response(200, content=catalog_bytes)
        if url.endswith("catalog.json.sig"):
            return httpx.Response(200, text=_sign(priv, catalog_bytes))
        if url.endswith(".zip"):
            return httpx.Response(200, content=zip_bytes)
        if url.endswith(".zip.sig"):
            return httpx.Response(200, text=sig)
        if url.endswith(".zip.sha256"):
            return httpx.Response(200, text=hashlib.sha256(zip_bytes).hexdigest())
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return PluginInstaller(
        root=tmp_path / "plugins",
        pubkey_path=pubkey_path,
        client=client,
        app_version="3.3.0",
    )


class TestInstallHappyPath:
    async def test_install_then_resolve_and_parse(self, tmp_path, keypair):
        from module.parser.analyser.providers.registry import registry

        zip_bytes = _make_plugin_zip()
        installer = _installer(tmp_path, keypair, zip_bytes)

        result = await installer.install(PLUGIN_ID)
        assert result.success is True
        assert result.version == VERSION

        adapter_cls = registry.resolve(PLUGIN_ID)
        assert adapter_cls.info.id == PLUGIN_ID
        assert adapter_cls.info.auth_kind == "device_code"

        # 装好的插件出现在列举里
        assert PLUGIN_ID in {i.id for i in registry.list_infos()}

        await installer.uninstall(PLUGIN_ID)
        registry.invalidate()


class TestInstallRejections:
    async def test_sha_mismatch_refused(self, tmp_path, keypair):
        priv, _ = keypair
        zip_bytes = _make_plugin_zip()
        bad_catalog = _catalog(zip_bytes, priv, extra={"sha256": "deadbeef"})
        installer = _installer(tmp_path, keypair, zip_bytes, catalog=bad_catalog)
        result = await installer.install(PLUGIN_ID)
        assert result.success is False
        assert (
            "sha256" in result.message.lower() or "checksum" in result.message.lower()
        )

    async def test_bad_signature_refused(self, tmp_path, keypair):
        zip_bytes = _make_plugin_zip()
        installer = _installer(tmp_path, keypair, zip_bytes, tamper_sig=True)
        result = await installer.install(PLUGIN_ID)
        assert result.success is False
        assert "signature" in result.message.lower()

    async def test_zip_slip_refused(self, tmp_path, keypair):
        zip_bytes = _make_plugin_zip(member_name="../evil.py")
        installer = _installer(tmp_path, keypair, zip_bytes)
        result = await installer.install(PLUGIN_ID)
        assert result.success is False

    async def test_incompatible_min_version_refused(self, tmp_path, keypair):
        priv, _ = keypair
        zip_bytes = _make_plugin_zip(manifest_extra={"min_ab_version": "9.9.0"})
        catalog = _catalog(zip_bytes, priv, extra={"min_ab_version": "9.9.0"})
        installer = _installer(tmp_path, keypair, zip_bytes, catalog=catalog)
        result = await installer.install(PLUGIN_ID)
        assert result.success is False
        assert "9.9.0" in result.message

    async def test_id_mismatch_refused(self, tmp_path, keypair):
        zip_bytes = _make_plugin_zip(manifest_extra={"id": "someone-else"})
        installer = _installer(tmp_path, keypair, zip_bytes)
        result = await installer.install(PLUGIN_ID)
        assert result.success is False

    async def test_unknown_plugin_id_refused(self, tmp_path, keypair):
        zip_bytes = _make_plugin_zip()
        installer = _installer(tmp_path, keypair, zip_bytes)
        result = await installer.install("nonexistent-in-catalog")
        assert result.success is False

    async def test_uninstall_builtin_refused(self, tmp_path, keypair):
        zip_bytes = _make_plugin_zip()
        installer = _installer(tmp_path, keypair, zip_bytes)
        result = await installer.uninstall("openai")
        assert result.success is False


class TestUninstallClearsCredential:
    async def test_uninstall_deletes_credential_row(self, tmp_path, keypair):
        from unittest.mock import AsyncMock, patch

        from module.parser.analyser.providers.registry import registry

        zip_bytes = _make_plugin_zip()
        installer = _installer(tmp_path, keypair, zip_bytes)
        await installer.install(PLUGIN_ID)

        db = AsyncMock()

        def _cm(v):
            cm = AsyncMock()
            cm.__aenter__ = AsyncMock(return_value=v)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm

        with patch("module.llm_plugins.installer.Database", return_value=_cm(db)):
            await installer.uninstall(PLUGIN_ID)

        db.llm_credential.delete.assert_awaited_once_with(PLUGIN_ID)
        registry.invalidate()

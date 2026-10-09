"""签名目录来源：通用插件的安装管线、加载器的 catalog 来源与安装 API。"""

import base64
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from ab_sdk.cli import main, pack
from ab_sdk.manifest import load_manifest
from module.models.config import Plugins
from module.plugin.installer import PLUGIN_PUBKEY_PATH, PluginInstaller
from module.plugin.loader import discover
from module.update.signing import DEFAULT_PUBKEY_PATH

PLUGIN_ID = "catalog-demo"


def load_catalog_script():
    script = Path(__file__).resolve().parents[3] / "scripts" / "build_plugin_catalog.py"
    spec = importlib.util.spec_from_file_location("build_plugin_catalog", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def keypair(tmp_path):
    priv = Ed25519PrivateKey.generate()
    pubkey_path = tmp_path / "pub.pem"
    pubkey_path.write_bytes(
        priv.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )
    return priv, pubkey_path


def build_zip(tmp_path: Path, *, edit=None, extra: dict[str, bytes] | None = None):
    """用 ab-plugin 脚手架与打包生成插件 zip；``edit`` 可在打包前改动目录。"""
    assert main(["new", PLUGIN_ID, "--dir", str(tmp_path / "src")]) == 0
    plugin_dir = tmp_path / "src" / PLUGIN_ID
    if edit:
        edit(plugin_dir)
    archive = pack(plugin_dir, tmp_path / "dist", load_manifest(plugin_dir))
    data = archive.read_bytes()
    if extra:
        buf = io.BytesIO(data)
        with zipfile.ZipFile(buf, "a") as zf:
            for name, content in extra.items():
                zf.writestr(name, content)
        data = buf.getvalue()
    return data


def make_installer(tmp_path, keypair, zip_bytes, *, entry=None, tamper_sig=False):
    priv, pubkey_path = keypair
    catalog_entry = {
        "id": PLUGIN_ID,
        "name": "Catalog demo",
        "version": "0.1.0",
        "kind": "plugin",
        "extension_points": ["rename_strategy"],
        "sdk": ">=0.5,<1",
        "min_ab_version": "4.0.0",
        "asset": f"{PLUGIN_ID}-0.1.0.zip",
        "sha256": hashlib.sha256(zip_bytes).hexdigest(),
    }
    catalog_entry.update(entry or {})
    catalog_bytes = json.dumps({"schema": 2, "plugins": [catalog_entry]}).encode()

    def sign(data: bytes) -> str:
        return base64.b64encode(priv.sign(data)).decode()

    zip_sig = base64.b64encode(b"\x00" * 64).decode() if tamper_sig else sign(zip_bytes)
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requested.append(url)
        assert "/releases/download/plugins/" in url
        if url.endswith("catalog.json"):
            return httpx.Response(200, content=catalog_bytes)
        if url.endswith("catalog.json.sig"):
            return httpx.Response(200, text=sign(catalog_bytes))
        if url.endswith(".zip"):
            return httpx.Response(200, content=zip_bytes)
        if url.endswith(".zip.sig"):
            return httpx.Response(200, text=zip_sig)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return PluginInstaller(
        root=tmp_path / "plugins",
        pubkey_path=pubkey_path,
        client=client,
        app_version="4.0.0",
    )


def discover_catalog(root: Path, tmp_path: Path):
    return discover(
        builtin_root=tmp_path / "no-builtin",
        catalog_root=root,
        local_root=root / "local",
        entry_point_group="ab-test-none",
    )


class TestInstall:
    async def test_install_version_changed_since_confirm_rejects(
        self, tmp_path, keypair
    ):
        installer = make_installer(tmp_path, keypair, build_zip(tmp_path))

        result = await installer.install(PLUGIN_ID, expected_version="0.0.9")

        assert not result.success and "0.1.0" in result.message
        assert not (tmp_path / "plugins" / PLUGIN_ID).exists()

    async def test_install_then_discover_load_and_uninstall(self, tmp_path, keypair):
        installer = make_installer(tmp_path, keypair, build_zip(tmp_path))

        result = await installer.install(PLUGIN_ID)

        assert result.success and result.version == "0.1.0"
        root = tmp_path / "plugins"
        assert (root / PLUGIN_ID / "0.1.0" / "plugin.toml").is_file()
        candidates, errors = discover_catalog(root, tmp_path)
        assert errors == []
        [candidate] = candidates
        assert candidate.source == "catalog" and candidate.signed
        assert candidate.load().__name__ == "CatalogDemoPlugin"

        assert (await installer.uninstall(PLUGIN_ID)).success
        assert discover_catalog(root, tmp_path)[0] == []

    async def test_upgrade_switches_to_new_version_directory(self, tmp_path, keypair):
        root = tmp_path / "plugins"
        old = await make_installer(tmp_path, keypair, build_zip(tmp_path)).install(
            PLUGIN_ID
        )
        assert old.success

        def bump(plugin_dir: Path) -> None:
            manifest = plugin_dir / "plugin.toml"
            manifest.write_text(manifest.read_text().replace("0.1.0", "0.2.0"))

        upgrade = tmp_path / "upgrade"
        upgrade.mkdir()
        installer = make_installer(
            upgrade,
            keypair,
            build_zip(upgrade, edit=bump),
            entry={"version": "0.2.0", "asset": f"{PLUGIN_ID}-0.2.0.zip"},
        )
        installer.root = root

        assert (await installer.install(PLUGIN_ID)).success
        [candidate] = discover_catalog(root, tmp_path)[0]
        assert candidate.manifest.version == "0.2.0"

    @pytest.mark.parametrize(
        "case, message",
        [
            ("sha", "sha256"),
            ("signature", "signature"),
            ("min_ab", "99.0.0"),
            ("unknown", "not found"),
            ("id", "id mismatch"),
            ("version", "version mismatch"),
            ("sdk", "ab_sdk"),
            ("native", "原生扩展"),
            ("zip-slip", "Unsafe path"),
        ],
    )
    async def test_rejected_bundle_installs_nothing(
        self, tmp_path, keypair, case, message
    ):
        def sdk_too_new(plugin_dir: Path) -> None:
            manifest = plugin_dir / "plugin.toml"
            manifest.write_text(manifest.read_text().replace(">=0.5", ">=9"))

        def with_native(plugin_dir: Path) -> None:
            (plugin_dir / "fast.so").write_bytes(b"\x7fELF")

        zip_bytes = build_zip(
            tmp_path,
            edit={"sdk": sdk_too_new, "native": with_native}.get(case),
            extra={"../evil.py": b"x"} if case == "zip-slip" else None,
        )
        entry = {
            "sha": {"sha256": "deadbeef"},
            "min_ab": {"min_ab_version": "99.0.0"},
            "id": {"id": "someone-else"},
            "version": {"version": "9.9.9"},
        }.get(case)
        installer = make_installer(
            tmp_path, keypair, zip_bytes, entry=entry, tamper_sig=case == "signature"
        )

        plugin_id = {"unknown": "other-plugin", "id": "someone-else"}.get(
            case, PLUGIN_ID
        )

        result = await installer.install(plugin_id)

        assert not result.success
        assert message.lower() in result.message.lower()
        assert discover_catalog(tmp_path / "plugins", tmp_path)[0] == []

    @pytest.mark.parametrize(
        "plugin_id", ["local", "core", "../outside", "Bad_Id", "rename"]
    )
    async def test_reserved_or_unsafe_id_refused_before_any_download(
        self, tmp_path, keypair, plugin_id
    ):
        installer = make_installer(tmp_path, keypair, build_zip(tmp_path))

        install = await installer.install(plugin_id)
        uninstall = await installer.uninstall(plugin_id)

        assert not install.success and not uninstall.success

    async def test_uninstall_leaves_unmanaged_directories_alone(
        self, tmp_path, keypair
    ):
        installer = make_installer(tmp_path, keypair, build_zip(tmp_path))
        # 本地插件目录与没有 installed.json 的目录都不属于安装器
        unmanaged = tmp_path / "plugins" / "hand-made"
        unmanaged.mkdir(parents=True)

        result = await installer.uninstall("hand-made")

        assert not result.success and unmanaged.is_dir()

    def test_default_pubkey_is_the_plugin_key_not_the_update_key(self):
        assert PluginInstaller().pubkey_path == PLUGIN_PUBKEY_PATH
        assert PLUGIN_PUBKEY_PATH != DEFAULT_PUBKEY_PATH
        # 公钥随 module/ 进入在线更新包，旧镜像更新后也有它
        assert PLUGIN_PUBKEY_PATH.is_file()

    async def test_uninstall_leaves_llm_provider_plugins_alone(self, tmp_path, keypair):
        installer = make_installer(tmp_path, keypair, build_zip(tmp_path))
        # LLM 插件：有 installed.json 与 plugin.json，没有 plugin.toml
        llm_dir = tmp_path / "plugins" / "github-copilot"
        (llm_dir / "1.0.0").mkdir(parents=True)
        (llm_dir / "1.0.0" / "plugin.json").write_text("{}")
        (llm_dir / "installed.json").write_text('{"version": "1.0.0"}')

        result = await installer.uninstall("github-copilot")

        assert not result.success and (llm_dir / "installed.json").is_file()


class TestReleaseScript:
    def test_empty_registry_builds_an_empty_signed_catalog(self, tmp_path, keypair):
        module = load_catalog_script()
        priv, _ = keypair
        key_path = tmp_path / "key.pem"
        key_path.write_bytes(
            priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        )
        catalog = module.build([], tmp_path / "release", key_path)
        assert json.loads(catalog.read_text())["plugins"] == []
        assert (tmp_path / "release" / "catalog.json.sig").is_file()

    # 默认 --min-ab 须放行 4.0 的 beta 宿主（semver 中 4.0.0-beta.N < 4.0.0）
    @pytest.mark.parametrize("app_version", ["4.0.0-beta.1", "4.0.0"])
    async def test_catalog_built_by_release_script_installs(
        self, tmp_path, keypair, app_version
    ):
        module = load_catalog_script()
        priv, pubkey_path = keypair
        key_path = tmp_path / "key.pem"
        key_path.write_bytes(
            priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        )
        archive = tmp_path / "pack" / f"{PLUGIN_ID}-0.1.0.zip"
        archive.parent.mkdir()
        archive.write_bytes(build_zip(tmp_path))

        source = {"repo": "alice/ab-demo", "commit": "a" * 40, "readme": "# demo"}
        module.build(
            [archive], tmp_path / "release", key_path, sources={PLUGIN_ID: source}
        )

        released = tmp_path / "release"

        def handler(request: httpx.Request) -> httpx.Response:
            name = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, content=(released / name).read_bytes())

        installer = PluginInstaller(
            root=tmp_path / "plugins",
            pubkey_path=pubkey_path,
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            app_version=app_version,
        )
        [entry] = await installer.fetch_catalog()
        assert entry["extension_points"] == ["rename_strategy"]
        assert {k: entry[k] for k in source} == source
        assert entry["has_web"] is False
        assert (await installer.install(PLUGIN_ID)).success


class TestLoaderCatalogSource:
    def test_priority_builtin_over_catalog_over_local(self, tmp_path):
        def write(root: Path, version: str) -> None:
            root.mkdir(parents=True)
            (root / "plugin.toml").write_text(
                f'[plugin]\nid = "dup"\nname = "{root.parts[-3]}"\n'
                f'version = "{version}"\nsdk = ">=0.1"\nentry = "dup:Dup"\n'
            )

        plugins = tmp_path / "plugins"
        write(plugins / "dup" / "1.0.0", "1.0.0")
        (plugins / "dup" / "installed.json").write_text('{"version": "1.0.0"}')
        write(plugins / "local" / "dup", "2.0.0")

        [candidate] = discover_catalog(plugins, tmp_path)[0]

        assert candidate.source == "catalog"

    def test_llm_plugins_and_broken_pointers_are_ignored(self, tmp_path):
        plugins = tmp_path / "plugins"
        (plugins / "github-copilot" / "1.0.0").mkdir(parents=True)
        (plugins / "github-copilot" / "1.0.0" / "plugin.json").write_text("{}")
        (plugins / "github-copilot" / "installed.json").write_text(
            '{"version": "1.0.0"}'
        )
        (plugins / "broken").mkdir()
        (plugins / "broken" / "installed.json").write_text("not json")

        candidates, errors = discover_catalog(plugins, tmp_path)

        assert candidates == [] and errors == []


class TestPluginsApi:
    @pytest.fixture
    def ctx(self, app, monkeypatch):
        from module.api import plugins as plugins_api
        from module.api.deps import get_context

        context = SimpleNamespace(
            plugins=SimpleNamespace(statuses=lambda: [], reload=AsyncMock()),
            settings=SimpleNamespace(plugins=Plugins(), save=MagicMock()),
        )
        monkeypatch.setattr(plugins_api, "settings", context.settings)
        app.dependency_overrides[get_context] = lambda: context
        monkeypatch.setattr(plugins_api, "CATALOG_ROOT", Path("/nonexistent"))
        return context

    def test_catalog_lists_entries(self, authed_client, ctx, monkeypatch):
        from module.api import plugins as plugins_api

        entry = {"id": PLUGIN_ID, "name": "Demo", "version": "1.0.0", "x": "ignored"}
        monkeypatch.setattr(
            plugins_api.PluginInstaller,
            "fetch_catalog",
            AsyncMock(return_value=[entry]),
        )

        response = authed_client.get("/api/v1/plugins/catalog")

        assert response.status_code == 200
        [item] = response.json()
        assert item["id"] == PLUGIN_ID and item["installed_version"] is None
        assert item["path"] == "."

    @pytest.mark.parametrize(
        ("installed", "expected"),
        [("1.0rc1", True), ("1.0.0", False), ("1.1.0", False), ("weird", True)],
    )
    def test_catalog_update_available_follows_pep440_order(
        self, authed_client, ctx, monkeypatch, installed, expected
    ):
        from module.api import plugins as plugins_api

        entry = {"id": PLUGIN_ID, "name": "Demo", "version": "1.0.0"}
        monkeypatch.setattr(
            plugins_api.PluginInstaller,
            "fetch_catalog",
            AsyncMock(return_value=[entry]),
        )
        monkeypatch.setattr(plugins_api, "installed_version", lambda *_: installed)

        [item] = authed_client.get("/api/v1/plugins/catalog").json()

        assert item["update_available"] is expected

    def test_catalog_unreachable_returns_502(self, authed_client, ctx, monkeypatch):
        from module.api import plugins as plugins_api

        monkeypatch.setattr(
            plugins_api.PluginInstaller,
            "fetch_catalog",
            AsyncMock(side_effect=httpx.ConnectError("down")),
        )

        assert authed_client.get("/api/v1/plugins/catalog").status_code == 502

    def test_install_enables_and_reloads_plugin(self, authed_client, ctx, monkeypatch):
        from module.api import plugins as plugins_api
        from module.plugin.installer import InstallResult

        monkeypatch.setattr(
            plugins_api.PluginInstaller,
            "install",
            AsyncMock(return_value=InstallResult(success=True, version="1.0.0")),
        )

        response = authed_client.post(f"/api/v1/plugins/{PLUGIN_ID}/install")

        assert response.status_code == 200
        assert ctx.settings.plugins.enabled[PLUGIN_ID] is True
        ctx.plugins.reload.assert_awaited_once_with(PLUGIN_ID)

    def test_failed_install_returns_400_without_enabling(
        self, authed_client, ctx, monkeypatch
    ):
        from module.api import plugins as plugins_api
        from module.plugin.installer import InstallResult

        monkeypatch.setattr(
            plugins_api.PluginInstaller,
            "install",
            AsyncMock(return_value=InstallResult(success=False, message="bad sig")),
        )

        response = authed_client.post(f"/api/v1/plugins/{PLUGIN_ID}/install")

        assert response.status_code == 400
        assert PLUGIN_ID not in ctx.settings.plugins.enabled
        ctx.plugins.reload.assert_not_awaited()

    def test_uninstall_reloads_plugin(self, authed_client, ctx, monkeypatch):
        from module.api import plugins as plugins_api
        from module.plugin.installer import InstallResult

        monkeypatch.setattr(
            plugins_api.PluginInstaller,
            "uninstall",
            AsyncMock(return_value=InstallResult(success=True)),
        )

        assert authed_client.delete(f"/api/v1/plugins/{PLUGIN_ID}").status_code == 200
        ctx.plugins.reload.assert_awaited_once_with(PLUGIN_ID)

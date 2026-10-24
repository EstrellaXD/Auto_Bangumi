"""插件市场索引工具 scripts/plugin_registry.py：条目解析、上架规则、测试门槛与增量构建。"""

import base64
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ab_sdk.cli import main, pack
from ab_sdk.manifest import load_manifest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "plugin_registry.py"
SHA = "a" * 40
PLUGIN_ID = "registry-demo"


@pytest.fixture(scope="module")
def reg():
    spec = importlib.util.spec_from_file_location("plugin_registry", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scaffold(tmp_path: Path, plugin_id: str = PLUGIN_ID) -> Path:
    assert main(["new", plugin_id, "--dir", str(tmp_path)]) == 0
    return tmp_path / plugin_id


def entry_text(**fields: str) -> str:
    data = {"repo": "alice/ab-demo", "commit": SHA} | fields
    return "".join(f'{k} = "{v}"\n' for k, v in data.items())


class TestEntryParse:
    def test_valid_entry_defaults_path_to_repo_root(self, reg):
        entry = reg.Entry.parse(PLUGIN_ID, entry_text())
        assert (entry.repo, entry.commit, entry.path) == ("alice/ab-demo", SHA, ".")

    @pytest.mark.parametrize(
        ("plugin_id", "text", "reason"),
        [
            (PLUGIN_ID, entry_text(commit="abc1234"), "40 位"),
            (PLUGIN_ID, entry_text(repo="https://github.com/a/b"), "owner/name"),
            (PLUGIN_ID, entry_text(path="../other"), "相对路径"),
            (PLUGIN_ID, entry_text(sha256="ABC"), "64 位"),
            (PLUGIN_ID, entry_text(tag="v1"), "未知字段"),
            (PLUGIN_ID, 'repo = "alice/ab-demo"\n', "缺少字段"),
            ("Bad_Id", entry_text(), "不是合法的插件 id"),
            ("local", entry_text(), "不是合法的插件 id"),
        ],
    )
    def test_invalid_entry_is_rejected(self, reg, plugin_id, text, reason):
        with pytest.raises(reg.Reject, match=reason):
            reg.Entry.parse(plugin_id, text)


class TestVerify:
    def test_matching_new_entry_passes(self, reg, tmp_path):
        src = scaffold(tmp_path)
        entry = reg.Entry.parse(PLUGIN_ID, entry_text())
        assert reg.verify(entry, src, None, None).id == PLUGIN_ID

    def test_file_name_must_match_manifest_id(self, reg, tmp_path):
        src = scaffold(tmp_path)
        entry = reg.Entry.parse("other-id", entry_text())
        with pytest.raises(reg.Reject, match="不一致"):
            reg.verify(entry, src, None, None)

    def test_builtin_id_is_rejected(self, reg, tmp_path):
        builtin = next(p.name for p in reg.BUILTIN_ROOT.iterdir() if p.is_dir())
        src = scaffold(tmp_path, builtin)
        entry = reg.Entry.parse(builtin, entry_text())
        with pytest.raises(reg.Reject, match="内置插件"):
            reg.verify(entry, src, None, None)

    def test_repo_cannot_change_on_update(self, reg, tmp_path):
        src = scaffold(tmp_path)
        entry = reg.Entry.parse(PLUGIN_ID, entry_text(repo="mallory/fork"))
        old = reg.Entry.parse(PLUGIN_ID, entry_text())
        with pytest.raises(reg.Reject, match="repo"):
            reg.verify(entry, src, old, "0.0.1")

    @pytest.mark.parametrize("old_version", ["0.1.0", "0.2.0"])
    def test_update_must_raise_version(self, reg, tmp_path, old_version):
        src = scaffold(tmp_path)  # 脚手架版本为 0.1.0
        entry = reg.Entry.parse(PLUGIN_ID, entry_text())
        with pytest.raises(reg.Reject, match="version 必须高于"):
            reg.verify(entry, src, entry, old_version)


class TestRunTests:
    def test_scaffold_tests_pass(self, reg, tmp_path):
        assert "passed" in reg.run_tests(scaffold(tmp_path))

    def test_zero_collected_tests_is_rejected(self, reg, tmp_path):
        src = scaffold(tmp_path)
        for test in (src / "tests").glob("test_*.py"):
            test.unlink()
        with pytest.raises(reg.Reject, match="没有收集到测试"):
            reg.run_tests(src)

    def test_failing_test_is_rejected(self, reg, tmp_path):
        src = scaffold(tmp_path)
        (src / "tests" / "test_fail.py").write_text("def test_x():\n    assert False\n")
        with pytest.raises(reg.Reject, match="测试失败"):
            reg.run_tests(src)


def test_committed_web_without_web_src_is_rejected(reg, tmp_path):
    src = scaffold(tmp_path)
    (src / "web").mkdir()
    (src / "web" / "index.js").write_text("export {}\n")
    with pytest.raises(reg.Reject, match="web-src"):
        reg.build_web(src)


def test_symlink_in_packed_files_is_rejected(reg, tmp_path):
    src = scaffold(tmp_path)
    (src / "leak").symlink_to("/etc/hosts")
    entry = reg.Entry.parse(PLUGIN_ID, entry_text())
    with pytest.raises(reg.Reject, match="符号链接"):
        reg.verify(entry, src, None, None)


def test_summary_escapes_author_output(reg):
    result = reg.Result(PLUGIN_ID, False, [("拒绝", "x |\n| tests | ✓ fake |")])
    text = reg.summary([result], [], [])
    assert "| tests | ✓ fake |" not in text
    assert "&#124;" in text


@pytest.mark.parametrize("given", ["", "e" * 64])
def test_check_tells_author_the_reviewed_sha256(reg, tmp_path, monkeypatch, given):
    src = scaffold(tmp_path / "src")
    text = entry_text(sha256=given) if given else entry_text()
    monkeypatch.setattr(
        reg,
        "_git",
        lambda *a: SimpleNamespace(
            returncode=0 if a[0] == "show" and "head" in a[1] else 1,
            stdout=text if a[0] == "show" else "",
        ),
    )
    monkeypatch.setattr(reg, "fetch", lambda entry, workdir: src)

    result = reg.check_entry(PLUGIN_ID, "base", "head", {}, tmp_path / "out", tmp_path)

    expected = hashlib.sha256(next((tmp_path / "out").glob("*.zip")).read_bytes())
    assert not result.ok
    assert result.lines[-1] == (
        "拒绝",
        f'在条目中写入 sha256 = "{expected.hexdigest()}"（当前为 {given or "空"}）',
    )


def test_unexpected_error_is_reported_per_entry(reg, tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "_git", lambda *a: (_ for _ in ()).throw(OSError("boom")))
    result = reg.check_entry(PLUGIN_ID, "base", "head", {}, tmp_path, tmp_path)
    assert not result.ok and result.lines == [("错误", "OSError: boom")]


DIGEST = "d" * 64


def published_catalog(**overrides):
    prev = {
        "id": PLUGIN_ID,
        "version": "0.1.0",
        "repo": "alice/ab-demo",
        "commit": SHA,
        "asset": f"{PLUGIN_ID}-0.1.0.zip",
        "sha256": DIGEST,
    }
    return {PLUGIN_ID: prev | overrides}


class TestPublish:
    @pytest.fixture
    def registry(self, reg, tmp_path, monkeypatch):
        root = tmp_path / "registry"
        root.mkdir()
        monkeypatch.setattr(reg, "REGISTRY", root)

        def write(sha256: str = DIGEST) -> None:
            (root / f"{PLUGIN_ID}.toml").write_text(entry_text(sha256=sha256))

        write()
        return write

    @pytest.fixture
    def built(self, reg, registry, tmp_path, monkeypatch):
        """脚手架插件经 build-one 打包；条目写入它审查过的 sha256。"""
        src = scaffold(tmp_path / "src")
        (src / "README.md").write_text("# demo\n")
        monkeypatch.setattr(reg, "fetch", lambda entry, workdir: src)
        data = pack(src, tmp_path / "probe", load_manifest(src)).read_bytes()
        registry(hashlib.sha256(data).hexdigest())
        out = tmp_path / "dist" / f"plugin-{PLUGIN_ID}"
        reg.build_one(PLUGIN_ID, out)
        return out, data

    @pytest.mark.parametrize(
        ("published", "rebuild", "expected"),
        [
            ({}, False, "build"),
            (published_catalog(), False, "reuse"),
            (published_catalog(), True, "build"),
            (published_catalog(commit="b" * 40), False, "build"),
            (published_catalog(path="other"), False, "build"),
            (published_catalog(sha256="e" * 64), False, "build"),
        ],
    )
    def test_plan_reuses_only_unchanged_sources(
        self, reg, registry, published, rebuild, expected
    ):
        assert reg.plan(published, rebuild)[expected] == [PLUGIN_ID]

    def test_collect_reuses_released_zip(self, reg, registry, tmp_path, monkeypatch):
        data = b"released zip"
        registry(hashlib.sha256(data).hexdigest())
        published = published_catalog(
            sha256=hashlib.sha256(data).hexdigest(), readme="hi"
        )
        monkeypatch.setattr(reg, "_download", lambda url: data)

        reg.collect(published, False, tmp_path / "dist", tmp_path / "stage")

        assert (tmp_path / "stage" / f"{PLUGIN_ID}-0.1.0.zip").read_bytes() == data
        sources = json.loads((tmp_path / "stage" / "sources.json").read_text())
        assert sources[PLUGIN_ID]["readme"] == "hi"

    def test_collect_rejects_reused_zip_with_wrong_sha256(
        self, reg, registry, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(reg, "_download", lambda url: b"tampered")
        with pytest.raises(SystemExit, match="sha256"):
            reg.collect(
                published_catalog(), False, tmp_path / "dist", tmp_path / "stage"
            )

    def test_build_one_then_collect(self, reg, built, tmp_path):
        reg.collect({}, False, tmp_path / "dist", tmp_path / "stage")

        assert (tmp_path / "stage" / f"{PLUGIN_ID}-0.1.0.zip").read_bytes() == built[1]
        sources = json.loads((tmp_path / "stage" / "sources.json").read_text())
        assert sources[PLUGIN_ID] == {
            "repo": "alice/ab-demo",
            "commit": SHA,
            "path": ".",
            "readme": "# demo\n",
        }

    def test_build_one_refuses_bytes_that_differ_from_review(
        self, reg, built, registry, tmp_path
    ):
        registry("e" * 64)
        with pytest.raises(reg.Reject, match="不一致"):
            reg.build_one(PLUGIN_ID, tmp_path / "again")

    @pytest.mark.parametrize("tamper", ["extra_zip", "wrong_source", "other_bytes"])
    def test_collect_rejects_tampered_build_output(self, reg, built, tmp_path, tamper):
        out, _ = built
        if tamper == "extra_zip":
            other = scaffold(tmp_path / "other", "other-plugin")
            pack(other, out, load_manifest(other))
        elif tamper == "wrong_source":
            (out / "source.json").write_text(
                json.dumps({"repo": "mallory/x", "commit": SHA, "path": "."})
            )
        else:
            zip_path = next(out.glob("*.zip"))
            with zipfile.ZipFile(zip_path, "a") as zf:
                zf.writestr("evil.py", "import os\n")
        with pytest.raises(SystemExit):
            reg.collect({}, False, tmp_path / "dist", tmp_path / "stage")


def test_diff_lists_registry_changes_between_commits(reg, tmp_path, monkeypatch):
    def git(*args: str) -> None:
        reg._run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], tmp_path)

    git("init", "-q")
    (tmp_path / "README.md").write_text("x\n")
    git("add", "-A")
    git("commit", "-qm", "base")
    (tmp_path / "plugins" / "registry").mkdir(parents=True)
    (tmp_path / "plugins" / "registry" / f"{PLUGIN_ID}.toml").write_text(entry_text())
    git("add", "-A")
    git("commit", "-qm", "add")
    monkeypatch.setattr(reg, "ROOT", tmp_path)

    changed = reg._diff("HEAD~1", "HEAD", "--diff-filter=AMR", "--", "plugins/registry")

    assert changed == [f"plugins/registry/{PLUGIN_ID}.toml"]


def test_symlinked_registry_entry_is_rejected(reg, tmp_path, monkeypatch):
    (tmp_path / "elsewhere.toml").write_text(entry_text())
    root = tmp_path / "registry"
    root.mkdir()
    (root / f"{PLUGIN_ID}.toml").symlink_to(tmp_path / "elsewhere.toml")
    monkeypatch.setattr(reg, "REGISTRY", root)
    with pytest.raises(reg.Reject, match="符号链接"):
        reg.registry_entries()


class TestLoadCatalog:
    @pytest.fixture
    def signed(self, reg, tmp_path, monkeypatch):
        priv = Ed25519PrivateKey.generate()
        pub = tmp_path / "pub.pem"
        pub.write_bytes(
            priv.public_key().public_bytes(
                Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
            )
        )
        monkeypatch.setattr(reg, "PLUGIN_PUBKEY", pub)
        catalog = tmp_path / "catalog.json"
        catalog.write_text(json.dumps({"schema": 2, "plugins": [{"id": PLUGIN_ID}]}))
        sig = tmp_path / "catalog.json.sig"
        sig.write_text(base64.b64encode(priv.sign(catalog.read_bytes())).decode())
        return catalog, sig

    def test_valid_signature_loads(self, reg, signed):
        assert list(reg.load_catalog(signed[0])) == [PLUGIN_ID]

    @pytest.mark.parametrize("tamper", ["catalog", "missing_sig"])
    def test_tampered_or_unsigned_catalog_is_refused(self, reg, signed, tamper):
        catalog, sig = signed
        if tamper == "catalog":
            catalog.write_text(json.dumps({"schema": 2, "plugins": []}))
        else:
            sig.unlink()
        with pytest.raises(SystemExit, match="签名"):
            reg.load_catalog(catalog)

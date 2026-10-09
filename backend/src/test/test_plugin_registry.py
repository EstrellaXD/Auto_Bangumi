"""插件市场索引工具 scripts/plugin_registry.py：条目解析、上架规则、测试门槛与增量构建。"""

import hashlib
import importlib.util
from pathlib import Path

import pytest

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


class TestBuild:
    @pytest.fixture
    def registry(self, reg, tmp_path, monkeypatch):
        root = tmp_path / "registry"
        root.mkdir()
        (root / f"{PLUGIN_ID}.toml").write_text(entry_text())
        monkeypatch.setattr(reg, "REGISTRY", root)
        return root

    def test_unchanged_commit_reuses_released_zip(
        self, reg, registry, tmp_path, monkeypatch
    ):
        src = scaffold(tmp_path / "src")
        archive = pack(src, tmp_path / "old", load_manifest(src))
        data = archive.read_bytes()
        old = {
            "plugins": [
                {
                    "id": PLUGIN_ID,
                    "version": "0.1.0",
                    "repo": "alice/ab-demo",
                    "commit": SHA,
                    "asset": archive.name,
                    "readme": "hi",
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ]
        }
        monkeypatch.setattr(reg, "_download", lambda url: data)
        monkeypatch.setattr(reg, "fetch", lambda *a: pytest.fail("must not fetch"))

        sources = reg.build(old, tmp_path / "out", tmp_path / "tmp")

        assert (tmp_path / "out" / archive.name).read_bytes() == data
        assert sources[PLUGIN_ID] == {
            "repo": "alice/ab-demo",
            "commit": SHA,
            "readme": "hi",
        }

    def test_reused_zip_with_wrong_sha256_fails(
        self, reg, registry, tmp_path, monkeypatch
    ):
        old = {
            "plugins": [
                {
                    "id": PLUGIN_ID,
                    "version": "0.1.0",
                    "repo": "alice/ab-demo",
                    "commit": SHA,
                    "asset": "x.zip",
                    "sha256": "0" * 64,
                }
            ]
        }
        monkeypatch.setattr(reg, "_download", lambda url: b"tampered")
        with pytest.raises(SystemExit, match="sha256"):
            reg.build(old, tmp_path / "out", tmp_path / "tmp")

    def test_changed_commit_is_fetched_and_packed(
        self, reg, registry, tmp_path, monkeypatch
    ):
        src = scaffold(tmp_path / "src")
        (src / "README.md").write_text("# demo\n")
        monkeypatch.setattr(reg, "fetch", lambda repo, commit, path, workdir: src)

        sources = reg.build({}, tmp_path / "out", tmp_path / "tmp")

        assert (tmp_path / "out" / f"{PLUGIN_ID}-0.1.0.zip").is_file()
        assert sources[PLUGIN_ID]["readme"] == "# demo\n"

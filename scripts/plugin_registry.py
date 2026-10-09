"""插件市场的索引工具：``plugins/registry/<id>.toml`` → 校验、测试、打包。

条目只有三个字段，代码留在作者自己的仓库，用完整 SHA 固定（tag 可以移动）::

    repo = "owner/name"
    commit = "<40 位 SHA>"
    path = "."            # 可选，插件在仓库中的子目录

用法（在仓库根目录运行；backend 的虚拟环境里有 ab_sdk）::

    uv run --project backend python scripts/plugin_registry.py check --base origin/4.0-dev --out dist
    uv run --project backend python scripts/plugin_registry.py build --old old/catalog.json --out dist

- ``check``：PR 上运行（没有 secret、只读权限）。只处理本 PR 改动的条目，运行作者的
  测试，把审查摘要（Markdown）写到 stdout，有条目不合格时以 1 退出。
- ``build``：合并后运行（同样没有密钥）。commit 未变的条目复用 release 中的 zip（按旧
  catalog 的 sha256 校验），其余拉取并打包，再写出 ``sources.json``。签名 job 只用
  ``build_plugin_catalog.py`` 读这些 zip，不运行作者的任何代码。
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from packaging.version import Version

from ab_sdk.cli import pack
from ab_sdk.manifest import ID_RE, MANIFEST_NAME, RESERVED_IDS, PluginManifest, check

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "plugins" / "registry"
BUILTIN_ROOT = ROOT / "backend" / "src" / "module" / "plugins" / "builtin"
PLUGIN_UI = ROOT / "webui" / "packages" / "plugin-ui"
RELEASE_BASE = "https://github.com/EstrellaXD/Auto_Bangumi/releases/download/plugins"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
README_LIMIT = 16 * 1024
_FIELDS = {"repo", "commit", "path"}


class Reject(Exception):
    """条目不合格；消息直接写进审查摘要。"""


@dataclass(frozen=True)
class Entry:
    id: str
    repo: str
    commit: str
    path: str = "."

    @classmethod
    def parse(cls, plugin_id: str, text: str) -> "Entry":
        if not ID_RE.match(plugin_id) or plugin_id in RESERVED_IDS:
            raise Reject(f"文件名 {plugin_id}.toml 不是合法的插件 id")
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise Reject(f"TOML 格式错误：{e}") from None
        if unknown := set(data) - _FIELDS:
            raise Reject(f"未知字段：{', '.join(sorted(unknown))}")
        if missing := {"repo", "commit"} - set(data):
            raise Reject(f"缺少字段：{', '.join(sorted(missing))}")
        entry = cls(
            plugin_id,
            str(data["repo"]),
            str(data["commit"]),
            str(data.get("path", ".")),
        )
        if not REPO_RE.match(entry.repo):
            raise Reject("repo 必须是 GitHub 的 owner/name")
        if not SHA_RE.match(entry.commit):
            raise Reject("commit 必须是 40 位完整 SHA")
        path = PurePosixPath(entry.path)
        if path.is_absolute() or ".." in path.parts:
            raise Reject("path 必须是仓库内的相对路径")
        return entry


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _tail(proc: subprocess.CompletedProcess[str], lines: int = 15) -> str:
    return "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-lines:])


def fetch(repo: str, commit: str, path: str, workdir: Path) -> Path:
    """浅拉取固定 commit，返回插件目录。不执行仓库里的任何代码。"""
    workdir.mkdir(parents=True, exist_ok=True)
    for cmd in (
        ["git", "init", "-q"],
        [
            "git",
            "fetch",
            "-q",
            "--depth",
            "1",
            f"https://github.com/{repo}.git",
            commit,
        ],
        ["git", "checkout", "-q", "FETCH_HEAD"],
    ):
        proc = _run(cmd, workdir)
        if proc.returncode != 0:
            raise Reject(f"无法拉取 {repo}@{commit[:7]}：{_tail(proc, 3)}")
    src = workdir / path
    if not (src / MANIFEST_NAME).is_file():
        raise Reject(f"{repo}@{commit[:7]} 的 {path} 下没有 {MANIFEST_NAME}")
    return src


def build_web(src: Path) -> None:
    """有 web-src/ 时丢弃提交的 web/，用 pnpm 从源码重新构建。"""
    web_src = src / "web-src"
    if not (web_src / "package.json").is_file():
        if (src / "web").exists():
            raise Reject("前端必须以 web-src/ 源码提交，CI 负责构建 web/")
        return
    if not (web_src / "pnpm-lock.yaml").is_file():
        raise Reject("web-src/ 必须带 pnpm-lock.yaml")
    shutil.rmtree(src / "web", ignore_errors=True)
    proc = _run(["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"], web_src)
    if proc.returncode != 0:
        raise Reject(f"pnpm install 失败：\n{_tail(proc)}")
    # 作者的 link: 路径指向自己机器上的 AB 仓库；统一换成本仓库的包
    linked = web_src / "node_modules" / "@autobangumi" / "plugin-ui"
    if linked.is_symlink() or linked.is_file():
        linked.unlink()
    elif linked.exists():
        shutil.rmtree(linked)
    linked.parent.mkdir(parents=True, exist_ok=True)
    linked.symlink_to(PLUGIN_UI, target_is_directory=True)
    proc = _run(["pnpm", "build"], web_src)
    if proc.returncode != 0:
        raise Reject(f"pnpm build 失败：\n{_tail(proc)}")


def verify(
    entry: Entry, src: Path, old: Entry | None, old_version: str | None
) -> PluginManifest:
    """清单与条目的一致性规则；不执行插件代码。"""
    manifest, problems = check(src)
    if manifest is None or problems:
        raise Reject("ab-plugin validate 失败：" + "；".join(problems))
    if manifest.id != entry.id:
        raise Reject(
            f"文件名 {entry.id}.toml 与 plugin.toml 的 id {manifest.id} 不一致"
        )
    if (BUILTIN_ROOT / entry.id).is_dir():
        raise Reject(f"id {entry.id} 与内置插件同名")
    if old is not None and old.repo != entry.repo:
        raise Reject("不能修改已上架插件的 repo：转移时先下架，再用新 repo 上架")
    if old_version is not None and Version(manifest.version) <= Version(old_version):
        raise Reject(f"version 必须高于已上架的 {old_version}")
    return manifest


def run_tests(src: Path) -> str:
    """运行作者的测试；至少 1 个且全部通过。返回 pytest 的结果行。"""
    if not (src / "tests").is_dir():
        raise Reject("缺少 tests/：至少要有 1 个测试")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--rootdir",
        str(src),
    ]
    if (src / "pyproject.toml").is_file():
        cmd += ["-c", str(src / "pyproject.toml")]
    proc = _run([*cmd, str(src / "tests")], src)
    if proc.returncode == 5:
        raise Reject("tests/ 中没有收集到测试：至少要有 1 个测试")
    if proc.returncode != 0:
        raise Reject(f"测试失败：\n{_tail(proc)}")
    return proc.stdout.strip().splitlines()[-1]


def readme(src: Path) -> str:
    for name in ("README.md", "readme.md", "README"):
        if (src / name).is_file():
            data = (src / name).read_bytes()[:README_LIMIT]
            return data.decode("utf-8", errors="ignore")
    return ""


def _manifest_version(repo: str, commit: str, path: str, workdir: Path) -> str:
    """已上架版本的 version：只读旧 commit 的 plugin.toml。"""
    src = fetch(repo, commit, path, workdir)
    return tomllib.loads((src / MANIFEST_NAME).read_text("utf-8"))["plugin"]["version"]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], ROOT)


# --------------------------------------------------------------------- check


@dataclass
class Result:
    id: str
    ok: bool
    lines: list[tuple[str, str]]


def check_entry(plugin_id: str, base: str, out: Path, tmp: Path) -> Result:
    rel = f"plugins/registry/{plugin_id}.toml"
    lines: list[tuple[str, str]] = []
    try:
        entry = Entry.parse(plugin_id, (ROOT / rel).read_text("utf-8"))
        old_text = _git("show", f"{base}:{rel}")
        old = (
            Entry.parse(plugin_id, old_text.stdout)
            if old_text.returncode == 0
            else None
        )
        old_version = (
            _manifest_version(old.repo, old.commit, old.path, tmp / "old")
            if old is not None
            else None
        )
        url = f"https://github.com/{entry.repo}"
        tree = f"{url}/tree/{entry.commit}" + (
            "" if entry.path == "." else f"/{entry.path}"
        )
        lines.append(
            ("审查", f"{url}/compare/{old.commit}...{entry.commit}" if old else tree)
        )
        src = fetch(entry.repo, entry.commit, entry.path, tmp / "new")
        has_web_src = (src / "web-src" / "package.json").is_file()
        build_web(src)
        manifest = verify(entry, src, old, old_version)
        version = (
            f"{old_version} → {manifest.version}" if old_version else manifest.version
        )
        lines.insert(0, ("版本", version))
        lines.append(("validate", "✓"))
        lines.append(("tests", f"✓ {run_tests(src)}"))
        lines.append(("扩展点", ", ".join(manifest.extension_points) or "—"))
        lines.append(("权限声明", ", ".join(manifest.permissions) or "无"))
        lines.append(("前端", "web-src/（CI 构建）" if has_web_src else "无"))
        archive = pack(src, out, manifest)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        lines.append(("zip", f"`{archive.name}` · sha256 `{digest}`"))
        return Result(plugin_id, True, lines)
    except Reject as e:
        lines.append(("拒绝", str(e)))
        return Result(plugin_id, False, lines)


def changed_ids(base: str) -> tuple[list[str], list[str]]:
    """本 PR 新增 / 修改与删除的条目 id。"""

    def ids(diff_filter: str) -> list[str]:
        proc = _git(
            "diff",
            "--name-only",
            f"--diff-filter={diff_filter}",
            f"{base}...HEAD",
            "--",
            "plugins/registry",
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr)
        return sorted(PurePosixPath(p).stem for p in proc.stdout.split())

    return ids("AMR"), ids("D")


def summary(results: list[Result], removed: list[str]) -> str:
    out = ["## 插件索引检查", ""]
    for r in results:
        out += [
            f"### {'✓' if r.ok else '✗'} {r.id}",
            "",
            "| 项目 | 结果 |",
            "| --- | --- |",
        ]
        out += [f"| {k} | {v.replace(chr(10), '<br>')} |" for k, v in r.lines]
        out.append("")
    if removed:
        out += ["### 下架", "", *[f"- {i}" for i in removed], ""]
    if not results and not removed:
        out.append("本 PR 没有改动 `plugins/registry/`。")
    return "\n".join(out)


def cmd_check(base: str, out: Path) -> int:
    changed, removed = changed_ids(base)
    with tempfile.TemporaryDirectory() as tmp:
        results = [check_entry(i, base, out, Path(tmp) / i) for i in changed]
    print(summary(results, removed))
    return 0 if all(r.ok for r in results) else 1


# --------------------------------------------------------------------- build


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


def build(old_catalog: dict, out: Path, tmp: Path) -> dict[str, dict[str, str]]:
    """重建全部条目的 zip，返回 sources（id → repo、commit、readme）。"""
    out.mkdir(parents=True, exist_ok=True)
    previous = {p["id"]: p for p in old_catalog.get("plugins", [])}
    sources: dict[str, dict[str, str]] = {}
    for path in sorted(REGISTRY.glob("*.toml")):
        entry = Entry.parse(path.stem, path.read_text("utf-8"))
        prev = previous.get(entry.id)
        if prev and (prev.get("repo"), prev.get("commit")) == (
            entry.repo,
            entry.commit,
        ):
            # commit 未变：复用已发布的 zip，作者删库或 force-push 不影响发布
            data = _download(f"{RELEASE_BASE}/{prev['asset']}")
            if hashlib.sha256(data).hexdigest() != prev["sha256"]:
                raise SystemExit(f"{prev['asset']} 与旧 catalog 的 sha256 不一致")
            (out / prev["asset"]).write_bytes(data)
            source = {"readme": prev.get("readme", "")}
            print(f"✓ {entry.id} {prev['version']} 复用", file=sys.stderr)
        else:
            src = fetch(entry.repo, entry.commit, entry.path, tmp / entry.id)
            build_web(src)
            manifest = verify(entry, src, None, None)
            pack(src, out, manifest)
            source = {"readme": readme(src)}
            print(f"✓ {entry.id} {manifest.version} 打包", file=sys.stderr)
        sources[entry.id] = {"repo": entry.repo, "commit": entry.commit, **source}
    return sources


def cmd_build(old: Path | None, out: Path) -> int:
    old_catalog = json.loads(old.read_text("utf-8")) if old and old.is_file() else {}
    with tempfile.TemporaryDirectory() as tmp:
        sources = build(old_catalog, out, Path(tmp))
    (out / "sources.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_check = sub.add_parser("check", help="检查本 PR 改动的条目")
    p_check.add_argument("--base", required=True)
    p_check.add_argument("--out", required=True, type=Path)
    p_build = sub.add_parser("build", help="重建全部条目的 zip 与 sources.json")
    p_build.add_argument("--old", type=Path, help="当前 release 的 catalog.json")
    p_build.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        sys.exit(
            cmd_check(args.base, args.out)
            if args.cmd == "check"
            else cmd_build(args.old, args.out)
        )
    except Reject as e:
        sys.exit(f"错误：{e}")

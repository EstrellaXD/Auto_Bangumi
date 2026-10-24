"""插件市场的索引工具：``plugins/registry/<id>.toml`` → 校验、测试、打包、汇总。

代码留在作者自己的仓库，用完整 SHA 固定（tag 可以移动）::

    repo = "owner/name"
    commit = "<40 位 SHA>"
    path = "."            # 可选，插件在仓库中的子目录
    sha256 = "<64 位>"    # PR 检查打出的 zip；签名只认这份审查过的字节

``sha256`` 留空时 PR 检查会给出应填的值。合并后重新打包的 zip 必须与它一致才会签名，
所以构建在 PR 和合并后产出不同字节时发布会失败，而不是签下没审过的内容。

在仓库根目录运行（backend 的虚拟环境里有 ab_sdk）::

    uv run --project backend python scripts/plugin_registry.py <命令> ...

- ``check``：PR 上运行（只读、没有 secret），用 base 分支的本脚本。只处理本 PR 改动
  的条目，运行作者的测试，把审查摘要（Markdown）写到 stdout；有条目不合格时以 1 退出。
- ``plan``：合并后列出要重新打包的条目（其余复用已发布的 zip）。不运行作者代码。
- ``build-one``：在独立的 job 里打包一个条目（会运行作者的前端构建，没有密钥）。
- ``collect``：签名 job 中运行，不运行作者代码。复用的 zip 自己下载并按旧 catalog 的
  sha256 校验；新打的 zip 逐个核对 id 与来源，再交给 ``build_plugin_catalog.py`` 签名。
  这样某个插件的构建即使被篡改，也只能影响它自己的 zip。
"""

import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from packaging.version import Version

from ab_sdk.cli import _PACK_EXCLUDE_DIRS, pack
from ab_sdk.manifest import ID_RE, MANIFEST_NAME, RESERVED_IDS, PluginManifest, check

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "plugins" / "registry"
BUILTIN_ROOT = ROOT / "backend" / "src" / "module" / "plugins" / "builtin"
PLUGIN_UI = ROOT / "webui" / "packages" / "plugin-ui"
PLUGIN_PUBKEY = ROOT / "backend" / "src" / "module" / "plugin" / "ab_plugin_pubkey.pem"
RELEASE_BASE = "https://github.com/EstrellaXD/Auto_Bangumi/releases/download/plugins"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
README_LIMIT = 16 * 1024
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = {"repo", "commit", "path", "sha256"}


class Reject(Exception):
    """条目不合格；消息直接写进审查摘要。"""


@dataclass(frozen=True)
class Entry:
    id: str
    repo: str
    commit: str
    path: str = "."
    sha256: str = ""

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
            str(data.get("sha256", "")),
        )
        if not REPO_RE.match(entry.repo):
            raise Reject("repo 必须是 GitHub 的 owner/name")
        if not SHA_RE.match(entry.commit):
            raise Reject("commit 必须是 40 位完整 SHA")
        path = PurePosixPath(entry.path)
        if path.is_absolute() or ".." in path.parts:
            raise Reject("path 必须是仓库内的相对路径")
        if entry.sha256 and not DIGEST_RE.match(entry.sha256):
            raise Reject("sha256 必须是 64 位小写十六进制")
        return entry

    @property
    def source(self) -> dict[str, str]:
        return {"repo": self.repo, "commit": self.commit, "path": self.path}


def registry_entries() -> list[Entry]:
    paths = sorted(REGISTRY.glob("*.toml"))
    if links := [p.name for p in paths if p.is_symlink()]:
        # 符号链接会把条目指向 registry 之外、未经检查的文件
        raise Reject(f"条目不能是符号链接：{', '.join(links)}")
    return [Entry.parse(p.stem, p.read_text("utf-8")) for p in paths]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _tail(proc: subprocess.CompletedProcess[str], lines: int = 15) -> str:
    return "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-lines:])


def fetch(entry: Entry, workdir: Path) -> Path:
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
            f"https://github.com/{entry.repo}.git",
            entry.commit,
        ],
        ["git", "checkout", "-q", "FETCH_HEAD"],
    ):
        proc = _run(cmd, workdir)
        if proc.returncode != 0:
            raise Reject(f"无法拉取 {entry.repo}@{entry.commit[:7]}：{_tail(proc, 3)}")
    src = workdir / entry.path
    if not src.resolve().is_relative_to(workdir.resolve()):
        raise Reject("path 经符号链接指向了仓库之外")
    if not (src / MANIFEST_NAME).is_file():
        raise Reject(
            f"{entry.repo}@{entry.commit[:7]} 的 {entry.path} 下没有 {MANIFEST_NAME}"
        )
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


def reject_symlinks(src: Path) -> None:
    """pack 会跟随符号链接读文件：要打包的部分里不允许有符号链接，
    否则作者可以把 runner 上的文件（如带 token 的 .git/config）打进签名包。"""
    for root, dirs, names in os.walk(src):
        dirs[:] = [d for d in dirs if d not in _PACK_EXCLUDE_DIRS]
        for name in dirs + names:
            if (Path(root) / name).is_symlink():
                raise Reject(f"不允许符号链接：{(Path(root) / name).relative_to(src)}")


def verify(
    entry: Entry, src: Path, old: Entry | None, old_version: str | None
) -> PluginManifest:
    """清单与条目的一致性规则；不执行插件代码。"""
    reject_symlinks(src)
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
    return _tail(proc, 1)


def readme(src: Path) -> str:
    for name in ("README.md", "readme.md", "README"):
        if (src / name).is_file():
            return (
                (src / name)
                .read_bytes()[:README_LIMIT]
                .decode("utf-8", errors="ignore")
            )
    return ""


def load_catalog(path: Path | None) -> dict[str, dict]:
    """已发布的 catalog：id → 条目。release 还不存在时为空。

    先验签：复用的 zip 与已上架版本都以它为准，能改 release 资源但没有签名密钥的
    人不能借下一次发布让篡改过的 zip 被重新签名。
    """
    if path is None or not path.is_file():
        return {}
    data = path.read_bytes()
    sig_path = path.with_name(path.name + ".sig")
    pubkey = load_pem_public_key(PLUGIN_PUBKEY.read_bytes())
    assert isinstance(pubkey, Ed25519PublicKey)
    try:
        pubkey.verify(base64.b64decode(sig_path.read_text().strip()), data)
    except (FileNotFoundError, ValueError, InvalidSignature):
        raise SystemExit(f"{path} 的签名无效或缺失") from None
    return {p["id"]: p for p in json.loads(data).get("plugins", [])}


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], ROOT)


# --------------------------------------------------------------------- check


@dataclass
class Result:
    id: str
    ok: bool
    lines: list[tuple[str, str]]


def check_entry(
    plugin_id: str,
    base: str,
    head: str,
    published: dict[str, dict],
    out: Path,
    tmp: Path,
) -> Result:
    rel = f"plugins/registry/{plugin_id}.toml"
    lines: list[tuple[str, str]] = []
    try:
        if _git("ls-tree", head, rel).stdout.startswith("120000"):
            raise Reject("条目不能是符号链接")
        entry = Entry.parse(plugin_id, _git("show", f"{head}:{rel}").stdout)
        old_text = _git("show", f"{base}:{rel}")
        old = (
            Entry.parse(plugin_id, old_text.stdout)
            if old_text.returncode == 0
            else None
        )
        # 已上架版本以已发布的 catalog 为准：旧 commit 可能已被作者删掉
        old_version = (
            published[plugin_id]["version"] if plugin_id in published else None
        )
        url = f"https://github.com/{entry.repo}"
        tree = f"{url}/tree/{entry.commit}" + (
            "" if entry.path == "." else f"/{entry.path}"
        )
        lines.append(
            ("审查", f"{url}/compare/{old.commit}...{entry.commit}" if old else tree)
        )
        src = fetch(entry, tmp)
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
        lines.append(("zip", f"{archive.name} · sha256 {digest}"))
        if entry.sha256 != digest:
            raise Reject(
                f'在条目中写入 sha256 = "{digest}"（当前为 {entry.sha256 or "空"}）'
            )
        return Result(plugin_id, True, lines)
    except Reject as e:
        lines.append(("拒绝", str(e)))
    except Exception as e:  # noqa: BLE001 - 一个条目出错不能让整份摘要丢失
        lines.append(("错误", f"{type(e).__name__}: {e}"))
    return Result(plugin_id, False, lines)


def _diff(base: str, head: str, *args: str) -> list[str]:
    proc = _git("diff", "--name-only", f"{base}...{head}", *args)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr)
    return proc.stdout.split()


def _cell(value: str) -> str:
    """作者控制的文本（测试输出等）进表格前转义，不能伪造行或链接。"""
    return html.escape(value).replace("|", "&#124;").replace("\n", "<br>")


def summary(results: list[Result], removed: list[str], others: list[str]) -> str:
    out = ["## 插件索引检查", ""]
    if others:
        out += [
            f"> **注意** 本 PR 还改动了 {len(others)} 个 `plugins/registry/` 以外的文件，需要另行审查。",
            "",
        ]
    for r in results:
        out += [
            f"### {'✓' if r.ok else '✗'} {r.id}",
            "",
            "| 项目 | 结果 |",
            "| --- | --- |",
        ]
        out += [f"| {k} | {_cell(v)} |" for k, v in r.lines]
        out.append("")
    if removed:
        out += ["### 下架", "", *[f"- {i}" for i in removed], ""]
    if not results and not removed:
        out.append("本 PR 没有改动 `plugins/registry/`。")
    return "\n".join(out)


def cmd_check(base: str, head: str, catalog: Path | None, out: Path) -> int:
    changed = sorted(
        PurePosixPath(p).stem
        for p in _diff(base, head, "--diff-filter=AMRT", "--", "plugins/registry")
    )
    removed = sorted(
        PurePosixPath(p).stem
        for p in _diff(base, head, "--diff-filter=D", "--", "plugins/registry")
    )
    others = [p for p in _diff(base, head) if not p.startswith("plugins/registry/")]
    published = load_catalog(catalog)
    with tempfile.TemporaryDirectory() as tmp:
        results = [
            check_entry(i, base, head, published, out, Path(tmp) / i) for i in changed
        ]
    print(summary(results, removed, others))
    return 0 if all(r.ok for r in results) else 1


# --------------------------------------------------------------------- publish


def plan(published: dict[str, dict], rebuild: bool) -> dict[str, list[str]]:
    """来源（repo、commit、path）与 sha256 都未变的条目复用已发布的 zip，其余重新打包。"""
    build: list[str] = []
    reuse: list[str] = []
    for entry in registry_entries():
        prev = published.get(entry.id, {})
        same = {
            k: prev.get(k, "." if k == "path" else None) for k in entry.source
        } == entry.source and prev.get("sha256") == entry.sha256
        (reuse if same and not rebuild else build).append(entry.id)
    return {"build": build, "reuse": reuse}


def build_one(plugin_id: str, out: Path) -> None:
    """打包一个条目，并写出 source.json（repo、commit、path、readme）。"""
    entry = Entry.parse(plugin_id, (REGISTRY / f"{plugin_id}.toml").read_text("utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = fetch(entry, Path(tmp))
        build_web(src)
        manifest = verify(entry, src, None, None)
        archive = pack(src, out, manifest)
        source = {**entry.source, "readme": readme(src)}
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != entry.sha256:
        raise Reject(
            f"打出的 zip sha256 {digest} 与条目中审查过的 {entry.sha256} 不一致"
        )
    (out / "source.json").write_text(
        json.dumps(source, ensure_ascii=False), encoding="utf-8"
    )


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read()


def _zip_id(archive: Path) -> str:
    with zipfile.ZipFile(archive) as zf:
        return tomllib.loads(zf.read(MANIFEST_NAME).decode("utf-8"))["plugin"]["id"]


def collect(published: dict[str, dict], rebuild: bool, dist: Path, stage: Path) -> None:
    """签名前的汇总：只放进 registry 中的条目，每个 zip 都核对过来源。

    ``dist/plugin-<id>/`` 是 build-one 各自的产物。复用的 zip 在这里下载，不经过
    运行作者代码的 job。
    """
    stage.mkdir(parents=True, exist_ok=True)
    todo = plan(published, rebuild)
    entries = {e.id: e for e in registry_entries()}
    sources: dict[str, dict[str, str]] = {}
    for plugin_id in todo["reuse"]:
        prev = published[plugin_id]
        data = _download(f"{RELEASE_BASE}/{prev['asset']}")
        if hashlib.sha256(data).hexdigest() != entries[plugin_id].sha256:
            raise SystemExit(f"{prev['asset']} 与条目中的 sha256 不一致")
        (stage / prev["asset"]).write_bytes(data)
        sources[plugin_id] = {
            **entries[plugin_id].source,
            "readme": prev.get("readme", ""),
        }
    for plugin_id in todo["build"]:
        built = dist / f"plugin-{plugin_id}"
        zips = sorted(built.glob("*.zip"))
        if len(zips) != 1 or _zip_id(zips[0]) != plugin_id:
            raise SystemExit(f"{plugin_id} 的构建产物不是恰好一个 id 相符的 zip")
        # 构建 job 运行过作者代码：只认条目里审查过的 sha256
        if (
            hashlib.sha256(zips[0].read_bytes()).hexdigest()
            != entries[plugin_id].sha256
        ):
            raise SystemExit(f"{plugin_id} 的构建产物与条目中的 sha256 不一致")
        source = json.loads((built / "source.json").read_text("utf-8"))
        if {k: source.get(k) for k in entries[plugin_id].source} != entries[
            plugin_id
        ].source:
            raise SystemExit(f"{plugin_id} 的构建产物来源与 registry 不一致")
        shutil.copy2(zips[0], stage / zips[0].name)
        sources[plugin_id] = {
            **entries[plugin_id].source,
            "readme": str(source.get("readme", ""))[:README_LIMIT],
        }
    (stage / "sources.json").write_text(
        json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="检查 PR 改动的条目")
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--catalog", type=Path, help="已发布的 catalog.json")
    p.add_argument("--out", required=True, type=Path)
    for name in ("plan", "collect"):
        p = sub.add_parser(name)
        p.add_argument("--catalog", type=Path)
        p.add_argument(
            "--rebuild", action="store_true", help="忽略已发布的 zip，全部重新打包"
        )
        if name == "collect":
            p.add_argument("--dist", required=True, type=Path)
            p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("build-one")
    p.add_argument("id")
    p.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.cmd == "check":
            sys.exit(cmd_check(args.base, args.head, args.catalog, args.out))
        elif args.cmd == "plan":
            print(json.dumps(plan(load_catalog(args.catalog), args.rebuild)))
        elif args.cmd == "build-one":
            build_one(args.id, args.out)
        else:
            collect(load_catalog(args.catalog), args.rebuild, args.dist, args.out)
    except Reject as e:
        sys.exit(f"错误：{e}")

"""``ab-plugin`` 命令行：``new`` / ``validate`` / ``pack`` / ``dev``。

只依赖 ``ab_sdk``，插件作者不需要安装宿主。
"""

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path
from string import Template

from . import SDK_VERSION, points
from .manifest import ID_RE, MANIFEST_NAME, TOOLING_DIRS, PluginManifest, check

# 打包时排除的目录名与文件后缀：开发产物、测试与作者侧的工程文件
_PACK_EXCLUDE_DIRS = TOOLING_DIRS | {"tests", "web-src"}  # web-src 是前端源码，运行时只用构建出的 web/
_PACK_EXCLUDE_FILES = frozenset({".DS_Store", "pyproject.toml", "uv.lock"})
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)  # 固定时间戳，同样的内容打出同样的 sha256

KINDS = ("rename", "notifier", "search")
POINTS = {
    "rename": points.RENAME_STRATEGY,
    "notifier": points.NOTIFIER,
    "search": points.SEARCH_SITE,
}

# --------------------------------------------------------------------- 脚手架

_MANIFEST = Template("""\
[plugin]
id = "$id"
name = "$name"
version = "0.1.0"
sdk = ">=$sdk_floor,<1"
entry = "$pkg:$cls"
description = ""
authors = []
extension_points = ["$point"]
""")

_PYPROJECT = Template("""\
# 只用于本地开发与测试，不会被打进插件包（ab-plugin pack 排除它）
[project]
name = "ab-plugin-$id"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["autobangumi-sdk"]

[dependency-groups]
dev = ["pytest>=8.0.0"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
""")

_CODE = {
    "rename": Template('''\
"""$name：重命名方式 $id。"""

from ab_sdk import Plugin, points, provider
from ab_sdk.rename import RenameInput, RenameStrategy, pad


class Strategy:
    def target_name(self, f: RenameInput) -> str:
        return f"{f.title} S{pad(f.season)}E{pad(f.episode)}{f.suffix}"


class $cls(Plugin):
    @provider(points.RENAME_STRATEGY, id="$id")
    def strategy(self) -> RenameStrategy:
        return Strategy()
'''),
    "notifier": Template('''\
"""$name：通知渠道 $id。"""

from ab_sdk import Plugin, points, provider
from ab_sdk.notify import NotificationMessage, NotifierFactory, NotifierSettings


class Channel:
    def __init__(self, settings: NotifierSettings) -> None:
        self.settings = settings

    async def send(self, message: NotificationMessage) -> bool:
        # 在这里把 message 投递到你的服务，成功返回 True
        return True

    async def test(self) -> tuple[bool, str]:
        ok = await self.send(
            NotificationMessage(kind="event", title="AutoBangumi", body="通知测试")
        )
        return ok, "ok" if ok else "发送失败"


class $cls(Plugin):
    @provider(points.NOTIFIER, id="$id")
    def channel(self) -> NotifierFactory:
        return Channel
'''),
    "search": Template('''\
"""$name：搜索站点 $id。"""

from ab_sdk import Plugin, points, provider
from ab_sdk.search import SearchSite


class $cls(Plugin):
    @provider(points.SEARCH_SITE, id="$id")
    def site(self) -> SearchSite:
        # %s 会被替换为关键词
        return SearchSite(url="https://example.org/rss?q=%s", parser="tmdb")
'''),
}

_TEST = {
    "rename": Template("""\
from ab_sdk.testing import RenameStrategyContract, create_plugin
from $pkg import $cls


class TestStrategy(RenameStrategyContract):
    def create(self):
        plugin, _ = create_plugin($cls)
        return plugin.strategy()
"""),
    "notifier": Template("""\
from ab_sdk.notify import NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin
from $pkg import $cls


class TestChannel(NotifierContract):
    def create(self):
        plugin, _ = create_plugin($cls)
        return plugin.channel()(NotifierSettings())
"""),
    "search": Template("""\
from ab_sdk.testing import SearchSiteContract, create_plugin
from $pkg import $cls


class TestSite(SearchSiteContract):
    def create(self):
        plugin, _ = create_plugin($cls)
        return plugin.site()
"""),
}

_README = Template("""\
# $name

AutoBangumi 插件。

```bash
uv run ab-plugin validate .   # 校验清单与 SDK 版本
uv run pytest                 # 契约测试
uv run ab-plugin dev .        # 链接到 config/plugins/local/ 并开启热重载
uv run ab-plugin pack .       # 打包为 dist/$id-<版本>.zip
```
""")


def scaffold(target: Path, plugin_id: str, kind: str) -> list[Path]:
    """在 ``target`` 下创建插件骨架，返回创建的文件。"""
    pkg = plugin_id.replace("-", "_")
    parts = {
        "point": POINTS[kind],
        "id": plugin_id,
        "name": plugin_id,
        "pkg": pkg,
        "cls": "".join(p.capitalize() for p in plugin_id.split("-")) + "Plugin",
        "sdk_floor": ".".join(SDK_VERSION.split(".")[:2]),
    }
    files = {
        MANIFEST_NAME: _MANIFEST,
        "pyproject.toml": _PYPROJECT,
        "README.md": _README,
        f"{pkg}/__init__.py": _CODE[kind],
        "tests/test_contract.py": _TEST[kind],
    }
    created = []
    for rel, template in files.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template.substitute(parts), encoding="utf-8")
        created.append(path)
    return created


# --------------------------------------------------------------------- 校验


def _report(plugin_dir: Path) -> PluginManifest | None:
    manifest, problems = check(plugin_dir)
    for problem in problems:
        print(f"错误：{problem}", file=sys.stderr)
    return None if problems else manifest


# --------------------------------------------------------------------- 打包


def pack(plugin_dir: Path, out_dir: Path, manifest: PluginManifest) -> Path:
    """打成 zip：内容在 zip 根（与签名目录的包布局一致），顺序与时间戳固定。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{manifest.id}-{manifest.version}.zip"
    entries = []
    for root, dirs, names in os.walk(plugin_dir):
        dirs[:] = sorted(d for d in dirs if d not in _PACK_EXCLUDE_DIRS)
        for name in names:
            if name in _PACK_EXCLUDE_FILES or name.endswith(".pyc"):
                continue
            path = Path(root) / name
            entries.append((path.relative_to(plugin_dir).as_posix(), path))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, path in sorted(entries):
            info = zipfile.ZipInfo(arcname, _ZIP_EPOCH)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    return target


# --------------------------------------------------------------------- dev


def _config_file(config_dir: Path) -> Path:
    # 开发版宿主读 config_dev.json，发布版读 config.json（module.conf.config）
    for name in ("config_dev.json", "config.json"):
        if (config_dir / name).is_file():
            return config_dir / name
    raise FileNotFoundError(f"{config_dir} 下没有配置文件，请先启动一次 AutoBangumi")


def link_dev(plugin_dir: Path, config_dir: Path, manifest: PluginManifest) -> Path:
    """软链到 ``<config>/plugins/local/<id>``，并开启 dev_mode、allow_unsigned 与该插件。"""
    config_path = _config_file(config_dir)
    link = config_dir / "plugins" / "local" / manifest.id
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if not (link.is_symlink() and link.resolve() == plugin_dir):
            raise FileExistsError(f"{link} 已存在且不指向 {plugin_dir}")
    else:
        link.symlink_to(plugin_dir, target_is_directory=True)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    plugins = config.setdefault("plugins", {})
    plugins["dev_mode"] = True
    plugins["allow_unsigned"] = True
    plugins.setdefault("enabled", {})[manifest.id] = True
    tmp = config_path.with_name(config_path.name + ".tmp")
    tmp.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, config_path)
    return link


# --------------------------------------------------------------------- 入口


def _cmd_new(args: argparse.Namespace) -> int:
    if not ID_RE.match(args.id):
        print("错误：id 只能由小写字母、数字和连字符组成", file=sys.stderr)
        return 1
    target = Path(args.dir) / args.id
    if target.exists():
        print(f"错误：{target} 已存在", file=sys.stderr)
        return 1
    scaffold(target, args.id, args.kind)
    print(f"已创建 {target}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    manifest = _report(Path(args.path).resolve())
    if manifest is None:
        return 1
    print(f"{manifest.id} {manifest.version}：通过（SDK {SDK_VERSION}）")
    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    plugin_dir = Path(args.path).resolve()
    manifest = _report(plugin_dir)
    if manifest is None:
        return 1
    print(pack(plugin_dir, Path(args.out), manifest))
    return 0


def _cmd_dev(args: argparse.Namespace) -> int:
    plugin_dir = Path(args.path).resolve()
    manifest = _report(plugin_dir)
    if manifest is None:
        return 1
    try:
        link = link_dev(plugin_dir, Path(args.config_dir), manifest)
    except OSError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    print(f"{link} -> {plugin_dir}")
    print("已开启 plugins.dev_mode：重启 AutoBangumi 后，修改该目录会自动重载插件。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ab-plugin", description="AutoBangumi 插件工具"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="创建插件骨架")
    new.add_argument("id", help="插件 id（小写字母、数字、连字符）")
    new.add_argument("--kind", choices=KINDS, default="rename", help="骨架类型")
    new.add_argument("--dir", default=".", help="在此目录下创建（默认当前目录）")
    new.set_defaults(func=_cmd_new)

    validate = sub.add_parser("validate", help="校验清单与 SDK 版本范围")
    validate.add_argument("path", nargs="?", default=".")
    validate.set_defaults(func=_cmd_validate)

    pack_cmd = sub.add_parser("pack", help="打包为可安装的 zip")
    pack_cmd.add_argument("path", nargs="?", default=".")
    pack_cmd.add_argument("-o", "--out", default="dist")
    pack_cmd.set_defaults(func=_cmd_pack)

    dev = sub.add_parser("dev", help="链接到 config/plugins/local/ 并开启热重载")
    dev.add_argument("path", nargs="?", default=".")
    dev.add_argument("--config-dir", default="config")
    dev.set_defaults(func=_cmd_dev)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

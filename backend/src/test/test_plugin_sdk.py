"""ab_sdk 的公开契约：边界约束与测试辅助。"""

import ast
from pathlib import Path

import pytest
from pydantic import BaseModel

import ab_sdk
from ab_sdk import Plugin, Verdict, hook, subscribe
from ab_sdk.rename import pad
from ab_sdk.testing import create_plugin

SDK_ROOT = Path(ab_sdk.__file__).parent


def test_sdk_does_not_import_host_internals():
    """ab_sdk 是对插件的稳定契约，不能依赖随时会重构的宿主模块。"""
    offenders = []
    for path in SDK_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            offenders += [
                f"{path.name}: {n}" for n in names if n.split(".")[0] == "module"
            ]
    assert offenders == []


class Options(BaseModel):
    keyword: str = "1080p"


class KeywordFilter(Plugin[Options]):
    config_model = Options

    @hook("torrent.filter")
    def check(self, title: str) -> Verdict:
        if self.config.keyword in title:
            return Verdict.ok()
        return Verdict.reject("missing keyword")

    @subscribe("*")
    async def remember(self, event):
        await self.ctx.kv.set("last", event.kind)


async def test_create_plugin_validates_options_and_drives_plugin(tmp_path):
    plugin, ctx = create_plugin(KeywordFilter, {"keyword": "4K"}, data_dir=tmp_path)
    await plugin.setup()
    assert plugin.check("[Group] Show - 01 [4K]").accept
    assert plugin.check("[Group] Show - 01 [1080p]") == Verdict(
        False, "missing keyword"
    )

    ctx.bus.subscribe("*", plugin.remember)
    await ctx.bus.deliver(ab_sdk.PluginLoaded(plugin_id="x", version="1"))
    assert await ctx.kv.get("last") == "plugin.loaded"


@pytest.mark.parametrize(
    ("value", "width", "expected"),
    [
        (5, 2, "05"),
        (0, 2, "00"),
        (12, 2, "12"),
        (123, 2, "123"),
        (12.0, 2, "12"),
        (9.5, 2, "09.5"),
        (12.5, 2, "12.5"),
        (7, 3, "007"),
    ],
)
def test_pad_number_keeps_fraction_and_zero_pads_whole(value, width, expected):
    assert pad(value, width) == expected

"""示例插件：带自有过滤器的重命名模板。

模板形如 ``{bangumi_name|sanitize} S{season|pad:2}E{episode|pad:2}``：
``{字段|过滤器|过滤器:参数}``，从左到右依次作用。渲染结果是文件名主体，字幕自动
追加 ``.语言``，最后追加扩展名。与内置 ``template``（Jinja2）不同，这里自带
过滤器表，不依赖第三方库。

模板写错在保存配置时就被拒绝（``field_validator``）。渲染出空名或含路径分隔符时
抛出 :class:`RenameSkipped`：宿主保留原文件名并通知用户，绝不改成别的名字。
"""

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ab_sdk import Plugin, points, provider
from ab_sdk.rename import RenameInput, RenameSkipped, RenameStrategy, pad

# 文件名里各系统都不允许的字符
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

FILTERS: dict[str, Callable[..., Any]] = {
    "pad": lambda v, width="2": pad(v, int(width)),
    "sanitize": lambda v: " ".join(_ILLEGAL.sub(" ", str(v)).split()),
    "short": lambda v, n="30": str(v)[: int(n)].rstrip(),
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
}
FIELDS = (
    "title",
    "bangumi_name",
    "season",
    "episode",
    "episode_type",
    "group",
    "kind",
    "language",
)
_TOKEN = re.compile(r"\{([^{}]*)\}")

SAMPLE = RenameInput(
    kind="media",
    media_path="[G] Sample - 01.mkv",
    title="Sample",
    bangumi_name="Sample (2024)",
    season=1,
    episode=1,
    suffix=".mkv",
    group="G",
)


def render(template: str, f: RenameInput) -> str:
    def expand(match: re.Match[str]) -> str:
        name, *chain = match.group(1).split("|")
        if name not in FIELDS:
            raise ValueError(f"未知字段 {name!r}，可用：{', '.join(FIELDS)}")
        value: Any = getattr(f, name) or ""
        for step in chain:
            fn, _, arg = step.partition(":")
            if fn not in FILTERS:
                raise ValueError(f"未知过滤器 {fn!r}，可用：{', '.join(FILTERS)}")
            value = FILTERS[fn](value, *([arg] if arg else []))
        return str(value)

    return _TOKEN.sub(expand, template)


class Options(BaseModel):
    template: str = Field(
        "{bangumi_name|sanitize} S{season|pad:2}E{episode|pad:2}",
        title="文件名模板",
        description=(
            "{字段|过滤器:参数}。字段：" + "、".join(FIELDS) + "。过滤器：pad:位数、"
            "sanitize（去掉非法字符）、short:长度、upper、lower"
        ),
    )

    @field_validator("template")
    @classmethod
    def _check(cls, value: str) -> str:
        render(value, SAMPLE)  # 字段或过滤器写错时抛 ValueError，保存配置返回 422
        return value


class Strategy:
    def __init__(self, template: str) -> None:
        self.template = template

    def target_name(self, f: RenameInput) -> str:
        stem = render(self.template, f).strip()
        if not stem.strip(".") or "/" in stem or "\\" in stem:
            raise RenameSkipped(f"模板渲染结果不可用：{stem!r}")
        language = f".{f.language}" if f.kind == "subtitle" and f.language else ""
        return f"{stem}{language}{f.suffix}"


class TemplateRename(Plugin[Options]):
    config_model = Options

    @provider(points.RENAME_STRATEGY, id="mini-template")
    def strategy(self) -> RenameStrategy:
        return Strategy(self.config.template)

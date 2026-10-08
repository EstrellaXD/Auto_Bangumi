"""template 重命名方式：用 Jinja2 沙箱模板生成文件名。

模板只负责文件名主体，扩展名（字幕为 ``.<语言><扩展名>``）由插件追加。
渲染结果为空、含路径分隔符或渲染出错时，宿主保持原文件名并记录错误。
"""

from typing import Any

from jinja2 import StrictUndefined, Template, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, Field, field_validator

from ab_sdk import Plugin, points, provider
from ab_sdk.rename import RenameInput

# 与内置 pn 方式的输出一致
DEFAULT_TEMPLATE = "{{ title }} S{{ season|pad(2) }}E{{ episode|pad(2) }}"
DEFAULT_MOVIE_TEMPLATE = "{{ title }}"


def pad(value: Any, width: int = 2) -> str:
    """整数部分补零到 ``width`` 位，保留小数集的小数部分（``5.5`` → ``05.5``）。"""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value)
    integer, dot, fraction = text.partition(".")
    sign = "-" if integer.startswith("-") else ""
    return f"{sign}{integer.lstrip('-').zfill(width)}{dot}{fraction}"


def build_environment() -> SandboxedEnvironment:
    # 沙箱禁止访问不安全的属性/方法；StrictUndefined 让拼错的变量名直接报错，
    # 而不是悄悄渲染成空字符串
    env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
    env.filters["pad"] = pad
    return env


def _check_syntax(value: str) -> str:
    if not value.strip():
        raise ValueError("模板不能为空")
    try:
        build_environment().from_string(value)
    except TemplateError as e:
        raise ValueError(f"模板语法错误：{e}") from e
    return value


class Options(BaseModel):
    template: str = Field(
        DEFAULT_TEMPLATE,
        title="剧集模板",
        description=(
            "可用变量：title、bangumi_name、season、episode、group、episode_type、"
            "kind、language；pad(n) 过滤器补零。扩展名会自动追加"
        ),
    )
    movie_template: str = Field(
        DEFAULT_MOVIE_TEMPLATE,
        title="剧场版模板",
        description="剧场版（episode_type 为 movie）使用的模板",
    )

    @field_validator("template", "movie_template")
    @classmethod
    def _validate(cls, value: str) -> str:
        return _check_syntax(value)


class TemplateStrategy:
    def __init__(self, template: str, movie_template: str) -> None:
        env = build_environment()
        self._template: Template = env.from_string(template)
        self._movie_template: Template = env.from_string(movie_template)

    def render(self, f: RenameInput) -> str:
        template = self._movie_template if f.episode_type == "movie" else self._template
        return template.render(
            title=f.title,
            bangumi_name=f.bangumi_name,
            season=f.season,
            episode=f.episode,
            group=f.group or "",
            episode_type=f.episode_type,
            kind=f.kind,
            language=f.language or "",
        ).strip()

    def target_name(self, f: RenameInput) -> str:
        name = self.render(f)
        if not name:
            raise ValueError("模板渲染结果为空")
        if "/" in name or "\\" in name:
            raise ValueError(f"模板渲染结果含路径分隔符：{name!r}")
        return f"{name}{f.full_suffix}"


class TemplateRename(Plugin[Options]):
    config_model = Options
    _strategy: TemplateStrategy | None = None

    @provider(points.RENAME_STRATEGY, id="template")
    def strategy(self) -> TemplateStrategy:
        # 宿主对每个文件都会调用一次工厂；配置变更时插件会被整体重建，
        # 因此按实例缓存编译好的模板即可
        if self._strategy is None:
            self._strategy = TemplateStrategy(
                self.config.template, self.config.movie_template
            )
        return self._strategy

"""内置插件：重命名方式 ``pn``、``advance`` 与 ``template``（``rename_strategy``）。

``pn`` / ``advance`` 的输出与 3.x 逐字节一致。``template`` 用 Jinja2 沙箱模板
渲染文件名主体（不含扩展名），字幕自动追加 ``.语言``，最后追加扩展名。

注意：title / bangumi_name 来自已存在于磁盘上的文件 / 文件夹名（单个路径分量），
不做保留字符清洗——追加清洗会让既有做种库（如含 ":" 的标题）在升级后被整库
批量重命名 (#721 评审)。电影 / 剧场版为 ``Title (Year).ext``，不使用 SxxExx。
"""

from jinja2 import StrictUndefined, Template, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, Field, field_validator

from ab_sdk import Plugin, PluginContext, points, provider
from ab_sdk.rename import RenameInput, RenameSkipped, RenameStrategy, pad

DEFAULT_TEMPLATE = "{{ title }} S{{ season|pad(2) }}E{{ episode|pad(2) }}"

# 保存配置时用它试渲染一次，渲染不出合法文件名的模板直接拒绝
SAMPLE = RenameInput(
    kind="media",
    media_path="[Group] Sample - 01 [1080p].mkv",
    title="Sample",
    bangumi_name="Sample (2024)",
    season=1,
    episode=1,
    suffix=".mkv",
    group="Group",
)

# StrictUndefined：写错变量名在保存时就报错，而不是渲染出空字符串
_env = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
_env.filters["pad"] = pad


def _language(f: RenameInput) -> str:
    return f".{f.language}" if f.kind == "subtitle" else ""


def standard_name(base: str, f: RenameInput) -> str:
    """``{base} SxxEyy[.语言].ext``；电影为 ``{base}[.语言].ext``。"""
    if f.episode_type == "movie":
        return f"{base}{_language(f)}{f.suffix}"
    return f"{base} S{pad(f.season)}E{pad(f.episode)}{_language(f)}{f.suffix}"


class PnRename:
    """``pn``：以文件名解析出的标题命名。"""

    def target_name(self, f: RenameInput) -> str:
        return standard_name(f.title, f)


class AdvanceRename:
    """``advance``：以番剧文件夹名命名。"""

    def target_name(self, f: RenameInput) -> str:
        return standard_name(f.bangumi_name, f)


class TemplateRename:
    """``template``：渲染失败或文件名不安全时抛出 RenameSkipped，宿主保留原名
    并通知用户。绝不退回到 pn。"""

    def __init__(self, template: Template) -> None:
        self._template = template

    def target_name(self, f: RenameInput) -> str:
        try:
            stem = self._template.render(
                title=f.title,
                bangumi_name=f.bangumi_name,
                season=f.season,
                episode=f.episode,
                episode_type=f.episode_type,
                group=f.group or "",
                kind=f.kind,
                language=f.language,
            ).strip()
        except Exception as e:
            raise RenameSkipped(f"模板渲染失败：{e}") from None
        if not stem or not stem.strip("."):
            raise RenameSkipped("模板渲染结果为空")
        if any(c in "/\\" or ord(c) < 32 for c in stem):
            raise RenameSkipped(f"模板渲染结果含路径分隔符或控制字符：{stem!r}")
        return f"{stem}{_language(f)}{f.suffix}"


def compile_template(source: str) -> TemplateRename:
    """编译并用示例文件试渲染；不合法时抛出 ValueError（保存配置时返回 422）。"""
    try:
        strategy = TemplateRename(_env.from_string(source))
    except TemplateError as e:
        raise ValueError(f"模板语法错误：{e}") from None
    try:
        strategy.target_name(SAMPLE)
    except RenameSkipped as e:
        raise ValueError(str(e)) from None
    return strategy


class Options(BaseModel):
    template: str = Field(
        DEFAULT_TEMPLATE,
        title="文件名模板",
        description=(
            "重命名方式选择 template 时使用的 Jinja2 模板，渲染文件名主体（不含"
            "扩展名，字幕会自动追加语言）。可用变量：title、bangumi_name、season、"
            "episode、episode_type（episode / movie / special）、group、kind"
            "（media / subtitle）、language；过滤器 pad(n) 把数字补零到 n 位。"
            "渲染失败或结果含路径分隔符的文件保留原名，并发送通知。"
        ),
    )

    @field_validator("template")
    @classmethod
    def _check_template(cls, value: str) -> str:
        compile_template(value)
        return value


class RenamePlugin(Plugin[Options]):
    config_model = Options

    def __init__(self, ctx: PluginContext) -> None:
        super().__init__(ctx)
        self._template = compile_template(self.config.template)

    @provider(points.RENAME_STRATEGY, id="pn")
    def pn_strategy(self) -> RenameStrategy:
        return PnRename()

    @provider(points.RENAME_STRATEGY, id="advance")
    def advance_strategy(self) -> RenameStrategy:
        return AdvanceRename()

    @provider(points.RENAME_STRATEGY, id="template")
    def template_strategy(self) -> RenameStrategy:
        return self._template

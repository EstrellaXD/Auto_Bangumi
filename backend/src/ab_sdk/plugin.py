from typing import ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel

from .context import PluginContext

ConfigT = TypeVar("ConfigT", bound=BaseModel, default=BaseModel)


class Plugin(Generic[ConfigT]):
    """插件入口基类。

    子类可声明 ``config_model``（pydantic 模型），宿主据此校验用户配置并生成
    WebUI 表单；以 ``Plugin[模型]`` 继承即可获得带类型的 ``self.config``。
    用 ``@hook`` / ``@provider`` / ``@subscribe`` 装饰方法来声明扩展。

    生命周期：宿主构造实例（传入 ctx）→ ``await setup()`` → 运行 →
    ``await teardown()``。配置变更时插件会被整体 teardown 后重新构造。
    """

    config_model: ClassVar[type[BaseModel] | None] = None

    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx

    @property
    def config(self) -> ConfigT:
        """按 ``config_model`` 校验后的配置。未声明 ``config_model`` 时抛错。"""
        if self.ctx.config is None:
            raise RuntimeError(f"{type(self).__name__} 未声明 config_model")
        return cast(ConfigT, self.ctx.config)

    async def setup(self) -> None:
        """加载后调用一次。抛出异常会让插件进入错误状态并被跳过。"""

    async def teardown(self) -> None:
        """卸载前调用一次，用于释放连接、取消后台任务等。"""

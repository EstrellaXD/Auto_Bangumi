"""插件配置模型的辅助函数。"""

from typing import Any

from pydantic import Field


def secret_field(default: str = "", *, description: str = "", **kwargs: Any) -> Any:
    """声明秘密字段（密码、令牌、Cookie 等）。

    WebUI 以密码框渲染；读取配置的接口只返回掩码，保存时收到掩码会保留原值。
    用法：``cookie: str = secret_field(description="站点 Cookie")``。
    """
    return Field(
        default, description=description, json_schema_extra={"secret": True}, **kwargs
    )

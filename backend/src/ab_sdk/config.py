"""插件配置模型的辅助函数。"""

from typing import Any

from pydantic import Field


def secret_field(default: Any = "", *, description: str = "", **kwargs: Any) -> Any:
    """声明秘密字段（密码、令牌、Cookie 等）。

    WebUI 以密码框渲染；读取配置的接口只返回掩码，保存时收到掩码会保留原值。
    用法：``cookie: str = secret_field(description="站点 Cookie")``。
    列表、字典整体声明为秘密时，其中每个值都掩码：
    ``urls: list[str] = secret_field(default_factory=list)``。
    """
    if "default_factory" not in kwargs:
        kwargs["default"] = default
    return Field(description=description, json_schema_extra={"secret": True}, **kwargs)

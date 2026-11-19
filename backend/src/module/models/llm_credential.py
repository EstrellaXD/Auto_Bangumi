"""订阅类 LLM 提供商的凭据行（OAuth/device-flow token）。

刻意存数据库而非 config：token 永远不进 ``settings.model_dump()``，因此不可能
经 ``GET /config/get`` 泄漏；前端只能通过 auth/status 看到连接状态。
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class LLMCredential(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    provider_id: str = Field(default="", index=True, unique=True)
    access_token: str = Field(default="")
    refresh_token: str = Field(default="")
    expires_at: float | None = Field(default=None)  # epoch 秒
    account_label: str = Field(default="")
    extra: str | None = Field(default=None)  # JSON 字符串（provider 自定义）
    updated_at: str = Field(default_factory=utcnow_iso)

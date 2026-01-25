"""
WebAuthn Passkey 数据模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Passkey(SQLModel, table=True):
    """存储 WebAuthn 凭证的数据库模型"""

    __tablename__ = "passkey"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    # 用户友好的名称 (e.g., "iPhone 15", "MacBook Pro")
    name: str = Field(min_length=1, max_length=64)

    # WebAuthn 核心字段
    credential_id: str = Field(unique=True, index=True)  # Base64URL encoded
    public_key: str  # CBOR encoded public key, Base64 stored
    sign_count: int = Field(default=0)  # 防止克隆攻击

    # 可选的设备信息
    aaguid: Optional[str] = None  # Authenticator AAGUID
    transports: Optional[str] = None  # JSON array: ["usb", "nfc", "ble", "internal"]

    # 审计字段
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None

    # 备份状态 (是否为多设备凭证，如 iCloud Keychain)
    backup_eligible: bool = Field(default=False)
    backup_state: bool = Field(default=False)


class PasskeyCreate(BaseModel):
    """创建 Passkey 的请求模型"""

    name: str = Field(min_length=1, max_length=64)
    # 注册完成后的 WebAuthn 响应
    attestation_response: dict


class PasskeyList(BaseModel):
    """返回给前端的 Passkey 列表（不含敏感数据）"""

    id: int
    name: str
    created_at: datetime
    last_used_at: Optional[datetime]
    backup_eligible: bool
    aaguid: Optional[str]


class PasskeyDelete(BaseModel):
    """删除 Passkey 请求"""

    passkey_id: int


class PasskeyAuthStart(BaseModel):
    """Passkey 认证开始请求"""

    username: Optional[str] = None  # Optional for discoverable credentials


class PasskeyAuthFinish(BaseModel):
    """Passkey 认证完成请求"""

    username: Optional[str] = None  # Optional for discoverable credentials
    credential: dict

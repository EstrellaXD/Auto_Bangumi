"""
认证策略抽象层
将密码认证和 Passkey 认证统一为策略模式
"""
from abc import ABC, abstractmethod

from sqlmodel import select

from module.database.engine import async_session_factory
from module.database.passkey import PasskeyDatabase
from module.models import ResponseModel
from module.models.user import User


class AuthStrategy(ABC):
    """认证策略基类"""

    @abstractmethod
    async def authenticate(
        self, username: str | None, credential: dict
    ) -> ResponseModel:
        """
        执行认证

        Args:
            username: 用户名（可选，用于可发现凭证模式）
            credential: 认证凭证（密码或 WebAuthn 响应）

        Returns:
            ResponseModel with status and user info
        """
        pass


class PasskeyAuthStrategy(AuthStrategy):
    """Passkey 认证策略"""

    def __init__(self, webauthn_service):
        self.webauthn_service = webauthn_service

    async def authenticate(
        self, username: str | None, credential: dict
    ) -> ResponseModel:
        """
        使用 WebAuthn Passkey 认证

        Args:
            username: 用户名（可选）。如果为 None，使用可发现凭证模式
            credential: WebAuthn 凭证响应
        """
        async with async_session_factory() as session:
            passkey_db = PasskeyDatabase(session)

            # 1. 提取 credential_id
            try:
                raw_id = credential.get("rawId")
                if not raw_id:
                    raise ValueError("Missing credential ID")

                credential_id_str = self.webauthn_service.base64url_encode(
                    self.webauthn_service.base64url_decode(raw_id)
                )
            except Exception:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en="Invalid passkey credential",
                    msg_zh="Passkey 凭证无效",
                )

            # 2. 查找 passkey
            passkey = await passkey_db.get_passkey_by_credential_id(credential_id_str)
            if not passkey:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en="Passkey not found",
                    msg_zh="未找到 Passkey",
                )

            # 3. 获取用户
            result = await session.execute(
                select(User).where(User.id == passkey.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en="User not found",
                    msg_zh="用户不存在",
                )

            # 4. 如果提供了 username，验证一致性
            if username and user.username != username:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en="Passkey does not belong to specified user",
                    msg_zh="Passkey 不属于指定用户",
                )

            # 5. 验证 WebAuthn 签名
            try:
                if username:
                    # Username-based mode
                    new_sign_count = self.webauthn_service.verify_authentication(
                        username, credential, passkey
                    )
                else:
                    # Discoverable credentials mode
                    new_sign_count = (
                        self.webauthn_service.verify_discoverable_authentication(
                            credential, passkey
                        )
                    )

                # 6. 更新使用记录
                await passkey_db.update_passkey_usage(passkey, new_sign_count)

                return ResponseModel(
                    status_code=200,
                    status=True,
                    msg_en="Login successfully with passkey",
                    msg_zh="通过 Passkey 登录成功",
                    data={"username": user.username},
                )

            except ValueError as e:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en=f"Passkey verification failed: {str(e)}",
                    msg_zh=f"Passkey 验证失败: {str(e)}",
                )

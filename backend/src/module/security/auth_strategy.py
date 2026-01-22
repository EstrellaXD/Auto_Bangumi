"""
认证策略抽象层
将密码认证和 Passkey 认证统一为策略模式
"""
import base64
from abc import ABC, abstractmethod

from module.database import Database
from module.models import ResponseModel
from module.models.user import User


class AuthStrategy(ABC):
    """认证策略基类"""

    @abstractmethod
    async def authenticate(self, username: str, credential: dict) -> ResponseModel:
        """
        执行认证

        Args:
            username: 用户名
            credential: 认证凭证（密码或 WebAuthn 响应）

        Returns:
            ResponseModel with status and user info
        """
        pass


class PasswordAuthStrategy(AuthStrategy):
    """密码认证策略（保持向后兼容）"""

    async def authenticate(self, username: str, credential: dict) -> ResponseModel:
        """使用密码认证"""
        password = credential.get("password")
        if not password:
            return ResponseModel(
                status_code=401,
                status=False,
                msg_en="Password is required",
                msg_zh="密码不能为空",
            )

        user = User(username=username, password=password)
        async with Database() as db:
            return await db.user.auth_user(user)


class PasskeyAuthStrategy(AuthStrategy):
    """Passkey 认证策略"""

    def __init__(self, webauthn_service):
        self.webauthn_service = webauthn_service

    async def authenticate(self, username: str, credential: dict) -> ResponseModel:
        """使用 WebAuthn Passkey 认证"""
        async with Database() as db:
            # 1. 查找用户
            try:
                user = await db.user.get_user(username)
            except Exception:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en="User not found",
                    msg_zh="用户不存在",
                )

            # 2. 提取 credential_id 并查找对应的 passkey
            try:
                raw_id = credential.get("rawId")
                if not raw_id:
                    raise ValueError("Missing credential ID")

                # 将 rawId 从 base64url 转换为标准格式
                credential_id_str = self.webauthn_service.base64url_encode(
                    self.webauthn_service.base64url_decode(raw_id)
                )

                passkey = await db.passkey.get_passkey_by_credential_id(credential_id_str)
                if not passkey or passkey.user_id != user.id:
                    raise ValueError("Passkey not found or not owned by user")

            except Exception as e:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en="Invalid passkey credential",
                    msg_zh="Passkey 凭证无效",
                )

            # 3. 验证 WebAuthn 签名
            try:
                new_sign_count = self.webauthn_service.verify_authentication(
                    username, credential, passkey
                )

                # 4. 更新使用记录
                await db.passkey.update_passkey_usage(passkey, new_sign_count)

                return ResponseModel(
                    status_code=200,
                    status=True,
                    msg_en="Login successfully with passkey",
                    msg_zh="通过 Passkey 登录成功",
                )

            except ValueError as e:
                return ResponseModel(
                    status_code=401,
                    status=False,
                    msg_en=f"Passkey verification failed: {str(e)}",
                    msg_zh=f"Passkey 验证失败: {str(e)}",
                )

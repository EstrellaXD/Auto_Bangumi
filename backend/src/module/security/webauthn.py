"""
WebAuthn 认证服务层
封装 py_webauthn 库的复杂性，提供清晰的注册和认证接口
"""
import base64
import json
import logging
from typing import List, Optional

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    CredentialDeviceType,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialType,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from module.models.passkey import Passkey

logger = logging.getLogger(__name__)


class WebAuthnService:
    """WebAuthn 核心业务逻辑"""

    def __init__(self, rp_id: str, rp_name: str, origin: str):
        """
        Args:
            rp_id: 依赖方 ID (e.g., "localhost" or "autobangumi.example.com")
            rp_name: 依赖方名称 (e.g., "AutoBangumi")
            origin: 前端 origin (e.g., "http://localhost:5173")
        """
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.origin = origin

        # 存储临时的 challenge（生产环境应使用 Redis）
        self._challenges: dict[str, bytes] = {}

    # ============ 注册流程 ============

    def generate_registration_options(
        self, username: str, user_id: int, existing_passkeys: List[Passkey]
    ) -> dict:
        """
        生成 WebAuthn 注册选项

        Args:
            username: 用户名
            user_id: 用户 ID（转为 bytes）
            existing_passkeys: 用户已有的 Passkey（用于排除）

        Returns:
            JSON-serializable registration options
        """
        # 将已有凭证转为排除列表
        exclude_credentials = [
            PublicKeyCredentialDescriptor(
                id=self.base64url_decode(pk.credential_id),
                type=PublicKeyCredentialType.PUBLIC_KEY,
                transports=self._parse_transports(pk.transports),
            )
            for pk in existing_passkeys
        ]

        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=str(user_id).encode("utf-8"),
            user_name=username,
            user_display_name=username,
            exclude_credentials=exclude_credentials if exclude_credentials else None,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,  # -7: ES256
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,  # -257: RS256
            ],
        )

        # 存储 challenge 用于后续验证
        challenge_key = f"reg_{username}"
        self._challenges[challenge_key] = options.challenge
        logger.debug(f"Generated registration challenge for {username}")

        return json.loads(options_to_json(options))

    def verify_registration(
        self, username: str, credential: dict, device_name: str
    ) -> Passkey:
        """
        验证注册响应并创建 Passkey 对象

        Args:
            username: 用户名
            credential: 来自前端的 credential 响应
            device_name: 用户输入的设备名称

        Returns:
            Passkey 对象（未保存到数据库）

        Raises:
            ValueError: 验证失败
        """
        challenge_key = f"reg_{username}"
        expected_challenge = self._challenges.get(challenge_key)
        if not expected_challenge:
            raise ValueError("Challenge not found or expired")

        try:
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=self.rp_id,
                expected_origin=self.origin,
            )

            # 构造 Passkey 对象
            passkey = Passkey(
                user_id=0,  # 调用方设置
                name=device_name,
                credential_id=self.base64url_encode(verification.credential_id),
                public_key=base64.b64encode(verification.credential_public_key).decode(
                    "utf-8"
                ),
                sign_count=verification.sign_count,
                aaguid=verification.aaguid if verification.aaguid else None,
                backup_eligible=verification.credential_device_type
                == CredentialDeviceType.MULTI_DEVICE,
                backup_state=verification.credential_backed_up,
            )

            logger.info(
                f"Successfully verified registration for {username}, device: {device_name}"
            )
            return passkey

        except Exception as e:
            logger.error(f"Registration verification failed: {e}")
            raise ValueError(f"Invalid registration response: {str(e)}")
        finally:
            # 清理使用过的 challenge（无论成功或失败都清理，防止重放攻击）
            self._challenges.pop(challenge_key, None)

    # ============ 认证流程 ============

    def generate_authentication_options(
        self, username: str, passkeys: List[Passkey]
    ) -> dict:
        """
        生成 WebAuthn 认证选项

        Args:
            username: 用户名
            passkeys: 用户的 Passkey 列表（限定可用凭证）

        Returns:
            JSON-serializable authentication options
        """
        allow_credentials = [
            PublicKeyCredentialDescriptor(
                id=self.base64url_decode(pk.credential_id),
                type=PublicKeyCredentialType.PUBLIC_KEY,
                transports=self._parse_transports(pk.transports),
            )
            for pk in passkeys
        ]

        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=allow_credentials if allow_credentials else None,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        # 存储 challenge
        challenge_key = f"auth_{username}"
        self._challenges[challenge_key] = options.challenge
        logger.debug(f"Generated authentication challenge for {username}")

        return json.loads(options_to_json(options))

    def verify_authentication(
        self, username: str, credential: dict, passkey: Passkey
    ) -> int:
        """
        验证认证响应

        Args:
            username: 用户名
            credential: 来自前端的 credential 响应
            passkey: 对应的 Passkey 对象

        Returns:
            新的 sign_count（用于更新数据库）

        Raises:
            ValueError: 验证失败
        """
        challenge_key = f"auth_{username}"
        expected_challenge = self._challenges.get(challenge_key)
        if not expected_challenge:
            raise ValueError("Challenge not found or expired")

        try:
            # 解码 public key
            credential_public_key = base64.b64decode(passkey.public_key)

            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=self.rp_id,
                expected_origin=self.origin,
                credential_public_key=credential_public_key,
                credential_current_sign_count=passkey.sign_count,
            )

            logger.info(f"Successfully verified authentication for {username}")
            return verification.new_sign_count

        except Exception as e:
            logger.error(f"Authentication verification failed: {e}")
            raise ValueError(f"Invalid authentication response: {str(e)}")
        finally:
            # 清理 challenge（无论成功或失败都清理，防止重放攻击）
            self._challenges.pop(challenge_key, None)

    # ============ 辅助方法 ============

    def _parse_transports(
        self, transports_json: Optional[str]
    ) -> List[AuthenticatorTransport]:
        """解析存储的 transports JSON"""
        if not transports_json:
            return []
        try:
            transport_strings = json.loads(transports_json)
            return [AuthenticatorTransport(t) for t in transport_strings]
        except Exception:
            return []

    def base64url_encode(self, data: bytes) -> str:
        """Base64URL 编码（无 padding）"""
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def base64url_decode(self, data: str) -> bytes:
        """Base64URL 解码（补齐 padding）"""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)


# 全局 WebAuthn 服务实例存储
_webauthn_services: dict[str, WebAuthnService] = {}


def get_webauthn_service(rp_id: str, rp_name: str, origin: str) -> WebAuthnService:
    """
    获取或创建 WebAuthnService 实例
    使用缓存以保持 challenge 状态
    """
    key = f"{rp_id}:{origin}"
    if key not in _webauthn_services:
        _webauthn_services[key] = WebAuthnService(rp_id, rp_name, origin)
    return _webauthn_services[key]

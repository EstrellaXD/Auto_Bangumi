"""
WebAuthn 认证服务层
封装 py_webauthn 库的复杂性，提供清晰的注册和认证接口
"""

import base64
import json
import logging
import time
from collections import OrderedDict
from typing import List, Optional

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    parse_authentication_credential_json,
    parse_client_data_json,
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

        self._CHALLENGE_TTL = 300
        self._CHALLENGE_MAX = 100
        # Keyed by base64url-encoded challenge value -> (challenge_bytes, created_at, logical_key)
        self._challenges: dict[str, tuple[bytes, float, str]] = {}

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [
            k
            for k, (_, ts, _) in self._challenges.items()
            if now - ts > self._CHALLENGE_TTL
        ]
        for k in expired:
            del self._challenges[k]

    def _store_challenge(self, logical_key: str, challenge: bytes) -> None:
        self._cleanup_expired()
        if len(self._challenges) >= self._CHALLENGE_MAX:
            oldest = min(self._challenges, key=lambda k: self._challenges[k][1])
            del self._challenges[oldest]
        b64key = self.base64url_encode(challenge)
        self._challenges[b64key] = (challenge, time.time(), logical_key)

    def _pop_challenge_by_key(self, logical_key: str) -> bytes | None:
        self._cleanup_expired()
        for b64key, (challenge, _, lk) in list(self._challenges.items()):
            if lk == logical_key:
                del self._challenges[b64key]
                return challenge
        return None

    def _pop_challenge_by_value(self, challenge: bytes) -> bytes | None:
        self._cleanup_expired()
        b64key = self.base64url_encode(challenge)
        entry = self._challenges.pop(b64key, None)
        if entry:
            return entry[0]
        return None

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
                resident_key=ResidentKeyRequirement.REQUIRED,  # Required for usernameless login
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            supported_pub_key_algs=[
                COSEAlgorithmIdentifier.ECDSA_SHA_256,  # -7: ES256
                COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,  # -257: RS256
            ],
        )

        self._store_challenge(f"reg_{username}", options.challenge)
        logger.debug("Generated registration challenge for %s", username)

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
        expected_challenge = self._pop_challenge_by_key(f"reg_{username}")
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

        self._store_challenge(f"auth_{username}", options.challenge)
        logger.debug("Generated authentication challenge for %s", username)

        return json.loads(options_to_json(options))

    def generate_discoverable_authentication_options(self) -> dict:
        """
        生成可发现凭证的认证选项（无需用户名）

        Returns:
            JSON-serializable authentication options without allowCredentials
        """
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=None,  # Empty = discoverable credentials mode
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        self._store_challenge(
            f"auth_discoverable_{self.base64url_encode(options.challenge)[:16]}",
            options.challenge,
        )
        logger.debug("Generated discoverable authentication challenge")

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
        expected_challenge = self._pop_challenge_by_key(f"auth_{username}")
        if not expected_challenge:
            raise ValueError("Challenge not found or expired")

        try:
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

    def verify_discoverable_authentication(
        self, credential: dict, passkey: Passkey
    ) -> int:
        """
        验证可发现凭证的认证响应（无需用户名）

        Args:
            credential: 来自前端的 credential 响应
            passkey: 通过 credential_id 查找到的 Passkey 对象

        Returns:
            新的 sign_count

        Raises:
            ValueError: 验证失败
        """
        # Pop the challenge the authenticator actually signed over (from
        # clientDataJSON), not just the first stored discoverable challenge —
        # with multiple concurrent discoverable logins in flight, popping by
        # position let one caller consume another caller's challenge.
        try:
            parsed_credential = parse_authentication_credential_json(credential)
            client_data = parse_client_data_json(
                parsed_credential.response.client_data_json
            )
        except Exception as e:
            logger.warning(f"Failed to parse discoverable authentication response: {e}")
            raise ValueError("Invalid authentication response")

        expected_challenge = self._pop_challenge_by_value(client_data.challenge)

        if not expected_challenge:
            raise ValueError("Challenge not found or expired")

        try:
            credential_public_key = base64.b64decode(passkey.public_key)

            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=expected_challenge,
                expected_rp_id=self.rp_id,
                expected_origin=self.origin,
                credential_public_key=credential_public_key,
                credential_current_sign_count=passkey.sign_count,
            )

            logger.info("Successfully verified discoverable authentication")
            return verification.new_sign_count

        except Exception as e:
            logger.error(f"Discoverable authentication verification failed: {e}")
            raise ValueError(f"Invalid authentication response: {str(e)}")

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
# Keyed by "rp_id:origin"; when rp_id/origin are derived from request headers
# (see api/passkey.py) a hostile client could otherwise grow this dict
# without bound, so it is capped as an LRU cache.
_WEBAUTHN_SERVICES_MAX = 8
_webauthn_services: "OrderedDict[str, WebAuthnService]" = OrderedDict()


def get_webauthn_service(rp_id: str, rp_name: str, origin: str) -> WebAuthnService:
    """
    获取或创建 WebAuthnService 实例
    使用缓存以保持 challenge 状态；缓存容量有限（LRU 淘汰）
    """
    key = f"{rp_id}:{origin}"
    if key in _webauthn_services:
        _webauthn_services.move_to_end(key)
        return _webauthn_services[key]
    if len(_webauthn_services) >= _WEBAUTHN_SERVICES_MAX:
        _webauthn_services.popitem(last=False)
    service = WebAuthnService(rp_id, rp_name, origin)
    _webauthn_services[key] = service
    return service

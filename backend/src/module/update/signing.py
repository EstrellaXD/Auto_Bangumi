"""更新包签名校验（ed25519）。

信任链：CI 用私钥（GitHub Secret ``UPDATE_SIGNING_KEY``）对
``update-bundle-*.zip`` 签名，公钥随镜像分发（``/app/ab_update_pubkey.pem``，
位于覆盖层不会替换的位置）。``apply_update`` 在解包前验签（尽早失败），
``boot_overlay`` 在每次启动时对留存的 zip 重新验签（安全边界——apply 时的
校验运行在可能已被覆盖的 module 代码里，不能作为最终依据）。

签名格式：对 zip 文件全部字节做 ed25519 签名，``.sig`` 文件内容为 base64 文本。
"""

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 相对运行时 cwd（容器内 /app，开发环境 backend/src）。
DEFAULT_PUBKEY_PATH = Path("ab_update_pubkey.pem")


def verify_bundle_signature(
    bundle_path: Path, signature_b64: str, pubkey_path: Path
) -> bool:
    """用 pubkey_path 的 PEM 公钥验证 bundle 的 ed25519 签名。

    任何失败（公钥缺失/损坏、签名格式错误、验签不通过、cryptography 不可用）
    都返回 False——调用方必须拒绝该更新包。
    """
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except ImportError:
        logger.error("[Update] cryptography unavailable; refusing unverified bundle")
        return False

    try:
        public_key = load_pem_public_key(pubkey_path.read_bytes())
        if not isinstance(public_key, Ed25519PublicKey):
            logger.error("[Update] pubkey is not ed25519; refusing bundle")
            return False
        signature = base64.b64decode(signature_b64.strip(), validate=True)
        public_key.verify(signature, bundle_path.read_bytes())
        return True
    except InvalidSignature:
        logger.error("[Update] bundle signature verification FAILED")
        return False
    except Exception as exc:  # noqa: BLE001 - 验签失败必须拒绝，不得放行
        logger.error("[Update] cannot verify bundle signature: %s", exc)
        return False

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from jwt import PyJWTError

_SECRET_PATH = Path("config/.jwt_secret")


def _load_or_create_secret() -> str:
    if _SECRET_PATH.exists():
        return _SECRET_PATH.read_text().strip()
    secret = secrets.token_hex(32)
    _SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SECRET_PATH.write_text(secret)
    _SECRET_PATH.chmod(0o600)
    return secret


app_pwd_key = _load_or_create_secret()
app_pwd_algorithm = "HS256"


# 创建 JWT Token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, app_pwd_key, algorithm=app_pwd_algorithm)
    return encoded_jwt


# 解码 Token
def decode_token(token: str | None):
    if not token:
        return None
    try:
        # 显式指定 algorithms，防止算法混淆攻击 (CVE-2024-33663 同类问题)
        payload = jwt.decode(token, app_pwd_key, algorithms=[app_pwd_algorithm])
        username = payload.get("sub")
        if username is None:
            return None
        return payload
    except PyJWTError:
        return None


def verify_token(token: str | None):
    # PyJWT 的 jwt.decode() 已经校验 "exp" 并在过期时抛出 PyJWTError（在上面
    # 被捕获），所以 decode_token() 返回的 token 永远不会是过期的——这里无需
    # 再单独检查过期时间。
    return decode_token(token)


# 密码加密&验证
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

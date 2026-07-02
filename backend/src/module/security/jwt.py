import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext

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

# Hashing 密码
app_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        payload = jwt.decode(token, app_pwd_key, algorithms=[app_pwd_algorithm])
        username = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None


def verify_token(token: str | None):
    # jose's jwt.decode() already validates "exp" and raises JWTError (caught
    # above) for expired tokens, so a token returned by decode_token() is
    # never expired — no separate expiry recheck is needed here.
    return decode_token(token)


# 密码加密&验证
def verify_password(plain_password, hashed_password):
    return app_pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return app_pwd_context.hash(password)

from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError


app_pwd_key = "auto_bangumi"
app_pwd_algorithm = "HS256"

# Hashing 密码
app_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 创建 JWT Token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, app_pwd_key, algorithm=app_pwd_algorithm)
    return encoded_jwt


# 解码 Token
def decode_token(token: str):
    try:
        payload = jwt.decode(token, app_pwd_key, algorithms=[app_pwd_algorithm])
        username = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None


def verify_token(token: str):
    token_data = decode_token(token)
    if token_data is None:
        return None
    expires = token_data.get("exp")
    if datetime.utcnow() >= datetime.fromtimestamp(expires):
        raise JWTError("Token expired")
    return token_data


# 密码加密&验证
def verify_password(plain_password, hashed_password):
    return app_pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return app_pwd_context.hash(password)

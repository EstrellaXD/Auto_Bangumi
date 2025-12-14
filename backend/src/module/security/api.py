from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from module.database import Database
from models.user import User, UserUpdate

from .jwt import verify_token, verify_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

active_user = []


async def get_current_user(token: str = Cookie(None)):
    if not token:
        raise UNAUTHORIZED
    payload = verify_token(token)
    if not payload:
        raise UNAUTHORIZED
    username = payload.get("sub")
    if not username:
        raise UNAUTHORIZED
    if username not in active_user:
        raise UNAUTHORIZED
    return username


async def get_token_data(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    return payload


def update_user_info(user_data: UserUpdate, current_user):
    try:
        with Database() as db:
            db.user.update_user(current_user, user_data)
        return True
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def auth_user(user: User) -> bool:
    with Database() as db:
        resp = db.user.get_user(user.username)
    if resp is None:
        return False
    res = verify_password(user.password, resp.password)
    if res:
        active_user.append(user.username)
    return res


UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from module.database.user import UserDatabase
from module.models.user import User

from .jwt import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    username = payload.get("sub")
    with UserDatabase as user_db:
        user = user_db.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username"
        )
    return user


async def get_token_data(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    return payload


def update_user_info(user_data: User, current_user):
    try:
        with UserDatabase as db:
            db.update_user(current_user.username, user_data)
        return True
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def auth_user(username, password):
    with UserDatabase() as db:
        db.auth_user(username, password)

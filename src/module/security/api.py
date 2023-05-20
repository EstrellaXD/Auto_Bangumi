from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .jwt import decode_token

from module.database.user import AuthDB
from module.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    username = payload.get("sub")
    with AuthDB() as user_db:
        user = user_db.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username")
    return user


async def get_token_data(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    return payload


def update_user_info(user_data: User, current_user):
    try:
        with AuthDB() as db:
            db.update_user(current_user.username, user_data)
        return {"message": "update success"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def auth_user(username, password):
    with AuthDB() as db:
        if not db.auth_user(username, password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")
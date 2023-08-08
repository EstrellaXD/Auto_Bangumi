from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from module.database import Database
from module.models.user import User, UserUpdate

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
    with Database() as db:
        user = db.user.get_user(username)
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


def update_user_info(user_data: UserUpdate, current_user):
    try:
        with Database() as db:
            db.user.update_user(current_user.username, user_data)
        return True
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def auth_user(user: User):
    with Database() as db:
        db.user.auth_user(user)


UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
)

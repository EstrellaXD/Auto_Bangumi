from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from module.database.user import AuthDB
from module.security.jwt import decode_token, oauth2_scheme

from .api import router


async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    username = payload.get("sub")
    user = user_db.get_user(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username")
    return user


async def get_token_data(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    return payload


@router.get("/api/v1/auth/login", response_model=dict, tags=["login"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    with AuthDB() as db:
        if not db.authenticate(username, password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")
        token = db.create_access_token(username)
        return {"access_token": token, "token_type": "bearer"}


@router.get("/api/v1/auth/logout", response_model=dict, tags=["login"])
async def logout(token_data: dict = Depends(get_token_data)):
    pass

@router.get("/api/v1/auth/refresh", response_model=dict, tags=["login"])
async def refresh(
        current_user: User = Depends(get_token_data),
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    token = create_access_token(current_user)
    return {"access_token": token, "token_type": "bearer"}


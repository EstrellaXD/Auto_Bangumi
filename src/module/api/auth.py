from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from module.database.user import AuthDB
from module.security.jwt import create_access_token, decode_token
from module.models.user import User

from .program import router

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


@router.post("/api/v1/auth/login", response_model=dict, tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    with AuthDB() as db:
        if not db.auth_user(username, password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")
        token = create_access_token({"sub": username})
        return {"access_token": token, "token_type": "bearer", "expire": 86400}


@router.get("/api/v1/auth/refresh_token", response_model=dict, tags=["auth"])
async def refresh(
        current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    token = create_access_token({"sub": current_user.username})
    return {"access_token": token, "token_type": "bearer", "expire": 86400}


@router.get("/api/v1/auth/logout", response_model=dict, tags=["auth"])
async def logout(
        current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    return {"message": "logout success"}


@router.post("/api/v1/auth/update", response_model=dict, tags=["auth"])
async def update_user(data: User, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    try:
        with AuthDB() as db:
            db.update_user(current_user.username, data)
        return {"message": "update success"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

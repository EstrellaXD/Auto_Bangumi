from datetime import timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from module.models.user import User
from module.security import (
    auth_user,
    create_access_token,
    get_current_user,
    update_user_info,
)

from .program import router


@router.post("/api/v1/auth/login", response_model=dict, tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    password = form_data.password
    auth_user(username, password)
    token = create_access_token(
        data={"sub": username}, expires_delta=timedelta(days=1)
    )

    return {"access_token": token, "token_type": "bearer", "expire": 86400}


@router.get("/api/v1/auth/refresh_token", response_model=dict, tags=["auth"])
async def refresh(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    token = create_access_token(
        data = {"sub": current_user.username}

    )
    return {"access_token": token, "token_type": "bearer", "expire": 86400}


@router.get("/api/v1/auth/logout", response_model=dict, tags=["auth"])
async def logout(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    return {"message": "logout success"}


@router.post("/api/v1/auth/update", response_model=dict, tags=["auth"])
async def update_user(user_data: User, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if update_user_info(user_data, current_user):
        return {
            "message": "update success",
            "access_token": create_access_token({"sub": user_data.username}),
            "token_type": "bearer",
            "expire": 86400,
        }

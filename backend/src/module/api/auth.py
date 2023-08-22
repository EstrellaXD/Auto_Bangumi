from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse

from module.models.user import User, UserUpdate
from module.models import APIResponse
from module.security.api import (
    auth_user,
    get_current_user,
    update_user_info,
)
from module.security.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=dict)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = User(username=form_data.username, password=form_data.password)
    auth_user(user)
    token = create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(days=1)
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access_token": token,
            "token_type": "bearer",
            "expire": 86400,
        },
    )


@router.get("/refresh_token", response_model=dict)
async def refresh(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    token = create_access_token(data={"sub": current_user.username})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access_token": token,
            "token_type": "bearer",
            "expire": 86400,
        },
    )


@router.get("/logout", response_model=APIResponse)
async def logout(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "msg_en": "Logout success",
            "msg_zh": "登出成功",
        },
    )


@router.post("/update", response_model=dict)
async def update_user(
    user_data: UserUpdate, current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if update_user_info(user_data, current_user):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "update success",
                "access_token": create_access_token({"sub": user_data.username}),
                "token_type": "bearer",
                "expire": 86400,
            },
        )

"""
Passkey 管理 API
用于注册、列表、删除 Passkey 凭证
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlmodel import select

from module.database.engine import async_session_factory
from module.database.passkey import PasskeyDatabase
from module.models import APIResponse
from module.models.passkey import (
    PasskeyAuthFinish,
    PasskeyAuthStart,
    PasskeyCreate,
    PasskeyDelete,
    PasskeyList,
)
from module.models.user import User
from module.security.api import active_user, get_current_user
from module.security.auth_strategy import PasskeyAuthStrategy
from module.security.jwt import create_access_token
from module.security.webauthn import get_webauthn_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/passkey", tags=["passkey"])


def _get_webauthn_from_request(request: Request):
    """
    从请求中构造 WebAuthnService
    优先使用浏览器的 Origin header（与 clientDataJSON 中的 origin 一致）
    """
    from urllib.parse import urlparse

    origin = request.headers.get("origin")
    if not origin:
        # Fallback: 从 Referer 或 Host 推断
        referer = request.headers.get("referer", "")
        if referer:
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"
        else:
            host = request.headers.get("host", "localhost:7892")
            forwarded_proto = request.headers.get("x-forwarded-proto")
            scheme = forwarded_proto if forwarded_proto else request.url.scheme
            origin = f"{scheme}://{host}"

    parsed_origin = urlparse(origin)
    rp_id = parsed_origin.hostname or "localhost"

    return get_webauthn_service(rp_id, "AutoBangumi", origin)


# ============ 注册流程 ============


@router.post("/register/options", response_model=dict)
async def get_registration_options(
    request: Request,
    username: str = Depends(get_current_user),
):
    """
    生成 Passkey 注册选项
    前端调用 navigator.credentials.create() 时使用
    """
    webauthn = _get_webauthn_from_request(request)

    async with async_session_factory() as session:
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Get existing passkeys
            passkey_db = PasskeyDatabase(session)
            existing_passkeys = await passkey_db.get_passkeys_by_user_id(user.id)

            options = webauthn.generate_registration_options(
                username=username,
                user_id=user.id,
                existing_passkeys=existing_passkeys,
            )

            return options

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate registration options: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/register/verify", response_model=APIResponse)
async def verify_registration(
    passkey_data: PasskeyCreate,
    request: Request,
    username: str = Depends(get_current_user),
):
    """
    验证 Passkey 注册响应并保存
    """
    webauthn = _get_webauthn_from_request(request)

    async with async_session_factory() as session:
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # 验证 WebAuthn 响应
            passkey = webauthn.verify_registration(
                username=username,
                credential=passkey_data.attestation_response,
                device_name=passkey_data.name,
            )

            # 设置 user_id 并保存
            passkey.user_id = user.id
            passkey_db = PasskeyDatabase(session)
            await passkey_db.create_passkey(passkey)

            return JSONResponse(
                status_code=200,
                content={
                    "msg_en": f"Passkey '{passkey_data.name}' registered successfully",
                    "msg_zh": f"Passkey '{passkey_data.name}' 注册成功",
                },
            )

        except ValueError as e:
            logger.warning(f"Registration verification failed for {username}: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to register passkey: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============ 认证流程 ============


@router.post("/auth/options", response_model=dict)
async def get_passkey_login_options(
    auth_data: PasskeyAuthStart,
    request: Request,
):
    """
    生成 Passkey 登录选项（challenge）
    前端先调用此接口，再调用 navigator.credentials.get()
    """
    webauthn = _get_webauthn_from_request(request)

    async with async_session_factory() as session:
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.username == auth_data.username)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            passkey_db = PasskeyDatabase(session)
            passkeys = await passkey_db.get_passkeys_by_user_id(user.id)

            if not passkeys:
                raise HTTPException(
                    status_code=400, detail="No passkeys registered for this user"
                )

            options = webauthn.generate_authentication_options(
                auth_data.username, passkeys
            )
            return options

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to generate login options: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/verify", response_model=dict)
async def login_with_passkey(
    auth_data: PasskeyAuthFinish,
    response: Response,
    request: Request,
):
    """
    使用 Passkey 登录（替代密码登录）
    """
    webauthn = _get_webauthn_from_request(request)

    strategy = PasskeyAuthStrategy(webauthn)
    resp = await strategy.authenticate(auth_data.username, auth_data.credential)

    if resp.status:
        token = create_access_token(
            data={"sub": auth_data.username}, expires_delta=timedelta(days=1)
        )
        response.set_cookie(key="token", value=token, httponly=True, max_age=86400)
        if auth_data.username not in active_user:
            active_user.append(auth_data.username)
        return {"access_token": token, "token_type": "bearer"}

    raise HTTPException(status_code=resp.status_code, detail=resp.msg_en)


# ============ Passkey 管理 ============


@router.get("/list", response_model=list[PasskeyList])
async def list_passkeys(username: str = Depends(get_current_user)):
    """获取用户的所有 Passkey"""
    async with async_session_factory() as session:
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            passkey_db = PasskeyDatabase(session)
            passkeys = await passkey_db.get_passkeys_by_user_id(user.id)

            return [passkey_db.to_list_model(pk) for pk in passkeys]

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to list passkeys: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=APIResponse)
async def delete_passkey(
    delete_data: PasskeyDelete,
    username: str = Depends(get_current_user),
):
    """删除 Passkey"""
    async with async_session_factory() as session:
        try:
            # Get user
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            passkey_db = PasskeyDatabase(session)
            await passkey_db.delete_passkey(delete_data.passkey_id, user.id)

            return JSONResponse(
                status_code=200,
                content={
                    "msg_en": "Passkey deleted successfully",
                    "msg_zh": "Passkey 删除成功",
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete passkey: {e}")
            raise HTTPException(status_code=500, detail=str(e))

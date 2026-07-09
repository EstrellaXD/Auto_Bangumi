"""Database-backed authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordRequestForm

from module.application.auth import (
    AuthenticationError,
    AuthenticationService,
    ConflictError,
    NotFoundError,
)
from module.models import APIResponse
from module.models.user import UserPublic, UserUpdate
from module.security.api import check_login_ip, get_auth_service, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

_TOKEN_MAX_AGE = 86400
_API_TOKEN_USER = "api_token_user"

AuthService = Annotated[AuthenticationService, Depends(get_auth_service)]
CurrentUser = Annotated[str, Depends(get_current_user)]


def _issue_token(token: str, response: Response) -> dict[str, str]:
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=_TOKEN_MAX_AGE,
        samesite="strict",
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=dict, dependencies=[Depends(check_login_ip)])
async def login(
    response: Response,
    service: AuthService,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Authenticate credentials and issue a persisted session."""
    try:
        _user, token = await service.login(form_data.username, form_data.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc
    return _issue_token(token, response)


async def _refresh_cookie(
    response: Response,
    token: str | None,
    service: AuthenticationService,
) -> dict[str, str]:
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = await service.refresh_session(token)
    if user is not None:
        return _issue_token(token, response)
    exchanged = await service.exchange_legacy_jwt(token)
    if exchanged is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    _user, persisted_token = exchanged
    return _issue_token(persisted_token, response)


@router.post("/refresh_token", response_model=dict)
async def refresh(
    response: Response,
    service: AuthService,
    token: str | None = Cookie(None),
):
    """Extend a persisted session or exchange a legacy JWT cookie."""
    return await _refresh_cookie(response, token, service)


@router.get("/refresh_token", response_model=dict, deprecated=True)
async def refresh_legacy_get(
    response: Response,
    service: AuthService,
    token: str | None = Cookie(None),
):
    """Compatibility alias; clients should use POST."""
    response.headers["Deprecation"] = "true"
    response.headers["Warning"] = '299 - "Use POST /auth/refresh_token"'
    return await _refresh_cookie(response, token, service)


@router.post("/logout", response_model=APIResponse)
async def logout(
    response: Response,
    service: AuthService,
    token: str | None = Cookie(None),
):
    """Revoke the current persisted session and clear its cookie."""
    if token:
        await service.logout(token)
    response.delete_cookie(key="token")
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Logout successfully.", "msg_zh": "登出成功。"},
    )


@router.get("/me", response_model=UserPublic)
async def me(current_user: CurrentUser, service: AuthService):
    if current_user in {_API_TOKEN_USER, "dev_user"}:
        raise HTTPException(status_code=400, detail="No database user for this session")
    try:
        return await service.get_user(current_user)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/update", response_model=dict)
async def update_user(
    user_data: UserUpdate,
    response: Response,
    current_user: CurrentUser,
    service: AuthService,
):
    """Update the current account and rotate all of its sessions."""
    if current_user in {_API_TOKEN_USER, "dev_user"}:
        raise HTTPException(
            status_code=400,
            detail="API token authentication cannot update user credentials.",
        )
    try:
        _user, token = await service.update_current_user(current_user, user_data)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {**_issue_token(token, response), "message": "update success"}

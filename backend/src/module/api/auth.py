"""Database-backed authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm

from module.application.auth import (
    AuthenticationError,
    AuthenticationService,
    ConflictError,
    NotFoundError,
)
from module.models import APIResponse
from module.models.user import (
    AuthenticationSuccess,
    UserCredentialsUpdate,
    UserPublic,
    UserUpdate,
)
from module.security.api import (
    AuthPrincipal,
    check_login_ip,
    get_auth_service,
    get_principal,
    require_session_principal,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_TOKEN_MAX_AGE = 86400

AuthService = Annotated[AuthenticationService, Depends(get_auth_service)]
Principal = Annotated[AuthPrincipal, Depends(get_principal)]
SessionPrincipal = Annotated[AuthPrincipal, Depends(require_session_principal)]


def _issue_session(token: str, response: Response) -> AuthenticationSuccess:
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=_TOKEN_MAX_AGE,
        samesite="strict",
    )
    return AuthenticationSuccess()


@router.post(
    "/login",
    response_model=AuthenticationSuccess,
    dependencies=[Depends(check_login_ip)],
)
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
    return _issue_session(token, response)


async def _refresh_cookie(
    response: Response,
    token: str | None,
    service: AuthenticationService,
) -> AuthenticationSuccess:
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = await service.refresh_session(token)
    if user is not None:
        return _issue_session(token, response)
    raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/refresh_token", response_model=AuthenticationSuccess)
async def refresh(
    response: Response,
    service: AuthService,
    token: str | None = Cookie(None),
):
    """Extend the persisted browser session carried by the cookie."""
    return await _refresh_cookie(response, token, service)


@router.get("/refresh_token", response_model=AuthenticationSuccess, deprecated=True)
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
    response.delete_cookie(key="token", httponly=True, samesite="strict")
    return APIResponse(
        status=True,
        msg_en="Logout successfully.",
        msg_zh="登出成功。",
    )


@router.get("/me", response_model=UserPublic)
async def me(principal: Principal):
    if principal.user is None:
        raise HTTPException(status_code=400, detail="No database user for this session")
    return principal.user


@router.post("/update", response_model=AuthenticationSuccess)
async def update_user(
    user_data: UserCredentialsUpdate,
    response: Response,
    principal: SessionPrincipal,
    service: AuthService,
):
    """Update the current account and rotate all of its sessions."""
    user = principal.user
    if user is None or user.id is None:
        raise HTTPException(status_code=403, detail="A browser session is required")
    try:
        update = UserUpdate(**user_data.model_dump(exclude_unset=True))
        _user, token = await service.update_current_user(user.id, update)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _issue_session(token, response)

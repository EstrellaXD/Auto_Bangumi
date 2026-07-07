from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2PasswordRequestForm

from module.models import APIResponse
from module.models.user import User, UserUpdate
from module.security.api import (
    active_user,
    auth_user,
    check_login_ip,
    get_current_user,
    update_user_info,
)
from module.security.jwt import create_access_token, decode_token

from .response import u_response

router = APIRouter(prefix="/auth", tags=["auth"])

_TOKEN_EXPIRY_DAYS = 1
_TOKEN_MAX_AGE = 86400

# Pseudo-username returned by get_current_user() for callers authenticated via
# a bearer API token (settings.security.login_tokens) rather than a cookie
# session. Such callers have no real session to refresh/logout/update.
_API_TOKEN_USER = "api_token_user"


def _issue_token(username: str, response: Response) -> dict:
    """Create a JWT, set it as an HttpOnly cookie, and return the bearer payload."""
    token = create_access_token(
        data={"sub": username}, expires_delta=timedelta(days=_TOKEN_EXPIRY_DAYS)
    )
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=_TOKEN_MAX_AGE,
        samesite="strict",
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=dict, dependencies=[Depends(check_login_ip)])
async def login(response: Response, form_data=Depends(OAuth2PasswordRequestForm)):
    """Authenticate with username/password and issue a session token."""
    user = User(username=form_data.username, password=form_data.password)
    resp = await auth_user(user)
    if resp.status:
        return _issue_token(user.username, response)
    return u_response(resp)


@router.get("/refresh_token", response_model=dict)
async def refresh(
    response: Response,
    token: str = Cookie(None),
    current_user: str = Depends(get_current_user),
):
    """Refresh the current session token and update the active-user timestamp."""
    if current_user == _API_TOKEN_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API token authentication has no cookie session to refresh.",
        )
    payload = decode_token(token)
    username = payload.get("sub") if payload else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    active_user.add(username)
    return _issue_token(username, response)


@router.post("/logout", response_model=APIResponse)
async def logout(
    response: Response,
    token: str = Cookie(None),
    current_user: str = Depends(get_current_user),
):
    """Invalidate the session and clear the token cookie."""
    if current_user != _API_TOKEN_USER:
        payload = decode_token(token)
        username = payload.get("sub") if payload else None
        if username:
            active_user.remove(username)
    response.delete_cookie(key="token")
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Logout successfully.", "msg_zh": "登出成功。"},
    )


@router.post("/update", response_model=dict)
async def update_user(
    user_data: UserUpdate,
    response: Response,
    token: str = Cookie(None),
    current_user: str = Depends(get_current_user),
):
    """Update credentials for the current user and re-issue a fresh token."""
    if current_user == _API_TOKEN_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API token authentication cannot update user credentials.",
        )
    payload = decode_token(token)
    old_user = payload.get("sub") if payload else None
    if not old_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    if await update_user_info(user_data, old_user):
        # Re-issue the token under the *new* username (if it changed) and
        # migrate the active-user session entry, so the old username isn't
        # left stranded (unable to log out) and the new one isn't rejected
        # as "not in active_user" on the very next request.
        new_username = user_data.username or old_user
        if new_username != old_user:
            active_user.remove(old_user)
            active_user.add(new_username)
        return {**_issue_token(new_username, response), "message": "update success"}

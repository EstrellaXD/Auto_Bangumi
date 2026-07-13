import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from module.application.auth import AuthenticationService
from module.composition import auth_service
from module.conf import settings
from module.database import Database
from module.models.user import User, UserUpdate

from .ip_allowlist import _is_allowed
from .jwt import verify_token

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Session lifetime mirrors the JWT expiry used at issuance (see auth.py /
# passkey.py, both timedelta(days=1)); the store is a secondary guard so a
# session cannot outlive its token.
SESSION_LIFETIME = timedelta(days=1)


class SessionStore:
    """In-memory registry of active usernames with lazy expiry.

    A username counts as present only while its recorded session is younger than
    ``lifetime``. Expired entries are evicted lazily on access. Replaces the bare
    module-global ``dict`` that never expired entries.
    """

    def __init__(self, lifetime: timedelta = SESSION_LIFETIME) -> None:
        self._lifetime = lifetime
        self._sessions: dict[str, datetime] = {}

    def add(self, username: str) -> None:
        self._sessions[username] = datetime.now()

    def remove(self, username: str) -> None:
        self._sessions.pop(username, None)

    def clear(self) -> None:
        """Invalidate every session (logout-all)."""
        self._sessions.clear()

    def __contains__(self, username: str) -> bool:
        issued = self._sessions.get(username)
        if issued is None:
            return False
        if datetime.now() - issued >= self._lifetime:
            self._sessions.pop(username, None)
            return False
        return True

    def __len__(self) -> int:
        return len(self._sessions)


active_user = SessionStore()

# Opt-in only: unlike the old `VERSION == "DEV_VERSION"` check (which was
# true for every unofficial/self-built image), this requires an explicit
# environment variable so auth can never be silently bypassed in production.
DEV_AUTH_BYPASS = os.environ.get("AB_DEV_NO_AUTH") == "1"

if DEV_AUTH_BYPASS:
    logger.warning(
        "!!! AB_DEV_NO_AUTH=1 is set — authentication is BYPASSED for every "
        "request. This must never be set in production. !!!"
    )


def check_login_ip(request: Request):
    """Dependency that enforces login IP whitelist.

    If ``settings.security.login_whitelist`` is empty, all IPs are allowed.
    """
    whitelist = settings.security.login_whitelist
    if not whitelist:
        return
    client_host = request.client.host if request.client else None
    if not client_host or not _is_allowed(client_host, whitelist):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP not in login whitelist",
        )


def get_auth_service() -> AuthenticationService:
    return auth_service


class CredentialKind(str, Enum):
    SESSION = "session"
    API_TOKEN = "api_token"
    DEVELOPMENT = "development"


@dataclass(frozen=True)
class AuthPrincipal:
    """Authenticated identity together with the credential that proved it."""

    username: str
    kind: CredentialKind
    user: User | None = None


async def get_principal(
    request: Request,
    token: str | None = Cookie(None),
    service: Annotated[AuthenticationService | None, Depends(get_auth_service)] = None,
) -> AuthPrincipal:
    """Resolve one supported credential into a typed principal.

    Accepts authentication via (in order of precedence):
    1. DEV_AUTH_BYPASS when ``AB_DEV_NO_AUTH=1`` is set in the environment.
    2. A persisted ``scope=api`` token in the ``Authorization`` header.
    3. An HttpOnly cookie containing a persisted session.

    Any explicit Authorization header takes precedence over a cookie. Browser
    session tokens and legacy plaintext/JWT credentials are deliberately not
    accepted in the header or cookie compatibility paths.
    """
    if DEV_AUTH_BYPASS:
        return AuthPrincipal(
            username="dev_user",
            kind=CredentialKind.DEVELOPMENT,
        )
    service = service or auth_service

    auth_header = request.headers.get("authorization", "")
    if auth_header:
        scheme, separator, api_token = auth_header.partition(" ")
        if not separator or scheme.lower() != "bearer" or not api_token:
            raise UNAUTHORIZED
        user = await service.authenticate_api_token(api_token, scope="api")
        if user is not None:
            return AuthPrincipal(
                username=user.username,
                kind=CredentialKind.API_TOKEN,
                user=user,
            )
        raise UNAUTHORIZED

    if not token:
        raise UNAUTHORIZED
    user = await service.authenticate_session(token)
    if user is not None:
        return AuthPrincipal(
            username=user.username,
            kind=CredentialKind.SESSION,
            user=user,
        )
    raise UNAUTHORIZED


async def get_current_user(
    principal: Annotated[AuthPrincipal, Depends(get_principal)],
) -> str:
    """Compatibility wrapper for data routes that only need a username."""
    return principal.username


async def require_session_principal(
    principal: Annotated[AuthPrincipal, Depends(get_principal)],
) -> AuthPrincipal:
    """Require a real browser cookie session for account-control operations."""
    if principal.kind is not CredentialKind.SESSION or principal.user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A browser session is required for this operation",
        )
    return principal


async def get_token_data(token: str = Depends(oauth2_scheme)):
    """FastAPI dependency that decodes and returns the OAuth2 bearer token payload."""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    return payload


async def update_user_info(user_data: UserUpdate, current_user):
    """Persist updated credentials for *current_user* to the database."""
    try:
        async with Database() as db:
            await db.user.update_user(current_user, user_data)
        return True
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


async def auth_user(user: User):
    """Verify credentials and register the user in ``active_user`` on success."""
    async with Database() as db:
        resp = await db.user.auth_user(user)
        if resp.status:
            active_user.add(user.username)
        return resp


UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
)

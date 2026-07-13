"""Database-backed API and MCP token management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from module.application.auth import (
    AuthenticationError,
    AuthenticationService,
    NotFoundError,
)
from module.models.auth import ApiTokenCreate, ApiTokenCreated, ApiTokenPublic
from module.security.api import (
    AuthPrincipal,
    get_auth_service,
    require_session_principal,
)

router = APIRouter(prefix="/tokens", tags=["tokens"])
AuthService = Annotated[AuthenticationService, Depends(get_auth_service)]
SessionPrincipal = Annotated[AuthPrincipal, Depends(require_session_principal)]


@router.get("", response_model=list[ApiTokenPublic])
async def list_tokens(_principal: SessionPrincipal, service: AuthService):
    return await service.list_api_tokens()


@router.post(
    "",
    response_model=ApiTokenCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_token(
    data: ApiTokenCreate,
    principal: SessionPrincipal,
    service: AuthService,
):
    user = principal.user
    if user is None or user.id is None:
        raise HTTPException(status_code=403, detail="A browser session is required")
    try:
        token, raw_token = await service.create_api_token_for_user_id(
            user.id,
            name=data.name,
            scope=data.scope,
            expires_at=data.expires_at,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
    return {**ApiTokenPublic.model_validate(token).model_dump(), "token": raw_token}


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: int,
    _principal: SessionPrincipal,
    service: AuthService,
):
    try:
        await service.revoke_api_token(token_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

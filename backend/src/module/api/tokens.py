"""Database-backed API and MCP token management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from module.application.auth import AuthenticationService, NotFoundError
from module.models.auth import ApiTokenCreate, ApiTokenCreated, ApiTokenPublic
from module.security.api import get_auth_service, get_current_user

router = APIRouter(prefix="/tokens", tags=["tokens"])
AuthService = Annotated[AuthenticationService, Depends(get_auth_service)]
CurrentUser = Annotated[str, Depends(get_current_user)]


@router.get("", response_model=list[ApiTokenPublic])
async def list_tokens(_current_user: CurrentUser, service: AuthService):
    return await service.list_api_tokens()


@router.post(
    "",
    response_model=ApiTokenCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_token(
    data: ApiTokenCreate,
    current_user: CurrentUser,
    service: AuthService,
):
    token, raw_token = await service.create_api_token_for_username(
        current_user,
        name=data.name,
        scope=data.scope,
        expires_at=data.expires_at,
    )
    return {**ApiTokenPublic.model_validate(token).model_dump(), "token": raw_token}


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: int,
    _current_user: CurrentUser,
    service: AuthService,
):
    try:
        await service.revoke_api_token(token_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)

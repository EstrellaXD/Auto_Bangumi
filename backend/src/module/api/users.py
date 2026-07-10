"""Authenticated multi-user management API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from module.application.auth import (
    AuthenticationService,
    ConflictError,
    NotFoundError,
)
from module.models.user import UserCreate, UserPublic, UserUpdate
from module.security.api import get_auth_service, require_session_principal

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_session_principal)],
)
AuthService = Annotated[AuthenticationService, Depends(get_auth_service)]


@router.get("", response_model=list[UserPublic])
async def list_users(service: AuthService):
    return await service.list_users()


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, service: AuthService):
    try:
        return await service.create_user(data)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(user_id: int, data: UserUpdate, service: AuthService):
    try:
        return await service.update_user(user_id, data)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, service: AuthService):
    try:
        await service.delete_user(user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return None

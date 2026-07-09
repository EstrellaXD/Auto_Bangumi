"""Async authentication and user-management use cases."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from module.models.auth import ApiToken
from module.models.user import User, UserCreate, UserUpdate
from module.ports import AuthUnitOfWork


class AuthenticationError(Exception):
    pass


class ConflictError(Exception):
    pass


class NotFoundError(Exception):
    pass


class AuthenticationService:
    def __init__(
        self,
        database_factory: Callable[[], AuthUnitOfWork],
        *,
        legacy_token_decoder: Callable[[str], dict[str, Any] | None] | None = None,
    ) -> None:
        self._database_factory = database_factory
        self._legacy_token_decoder = legacy_token_decoder or (lambda _token: None)

    @staticmethod
    def _user_id(user: User) -> int:
        if user.id is None:
            raise RuntimeError("Persisted user has no primary key")
        return user.id

    async def login(self, username: str, password: str) -> tuple[User, str]:
        async with self._database_factory() as db:
            user = await db.user.authenticate_credentials(username, password)
            if user is None:
                raise AuthenticationError("Invalid username or password")
            return user, await db.auth.create_session(self._user_id(user))

    async def authenticate_session(self, token: str) -> User | None:
        async with self._database_factory() as db:
            return await db.auth.authenticate_session(token)

    async def authenticate_api_token(
        self, token: str, *, scope: str = "api"
    ) -> User | None:
        async with self._database_factory() as db:
            return await db.auth.authenticate_api_token(token, scope=scope)

    async def authenticate_legacy_jwt(self, token: str) -> User | None:
        payload = self._legacy_token_decoder(token)
        username = payload.get("sub") if payload else None
        if not username:
            return None
        async with self._database_factory() as db:
            user = await db.user.find_user(username)
            return user if user and user.enabled else None

    async def exchange_legacy_jwt(self, token: str) -> tuple[User, str] | None:
        user = await self.authenticate_legacy_jwt(token)
        if user is None:
            return None
        async with self._database_factory() as db:
            return user, await db.auth.create_session(self._user_id(user))

    async def refresh_session(
        self, token: str, *, ttl: timedelta = timedelta(days=1)
    ) -> User | None:
        async with self._database_factory() as db:
            return await db.auth.refresh_session(token, ttl=ttl)

    async def logout(self, token: str) -> bool:
        async with self._database_factory() as db:
            return await db.auth.revoke_session(token)

    async def issue_session_for_username(self, username: str) -> str:
        async with self._database_factory() as db:
            user = await db.user.find_user(username)
            if user is None or not user.enabled:
                raise AuthenticationError("User is not available")
            return await db.auth.create_session(self._user_id(user))

    async def get_user(self, username: str) -> User:
        async with self._database_factory() as db:
            user = await db.user.find_user(username)
            if user is None:
                raise NotFoundError("User not found")
            return user

    async def list_users(self) -> list[User]:
        async with self._database_factory() as db:
            return await db.user.list_users()

    async def create_user(self, data: UserCreate) -> User:
        try:
            async with self._database_factory() as db:
                return await db.user.create_user(data.username, data.password)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        try:
            async with self._database_factory() as db:
                user = await db.user.update_user_by_id(user_id, data)
                if data.password or data.enabled is False:
                    await db.auth.revoke_user_sessions(user_id)
                return user
        except ValueError as exc:
            if str(exc) == "User not found":
                raise NotFoundError(str(exc)) from exc
            raise ConflictError(str(exc)) from exc

    async def update_current_user(
        self, username: str, data: UserUpdate
    ) -> tuple[User, str]:
        async with self._database_factory() as db:
            current = await db.user.find_user(username)
            if current is None:
                raise NotFoundError("User not found")
            try:
                user = await db.user.update_user_by_id(self._user_id(current), data)
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc
            user_id = self._user_id(user)
            await db.auth.revoke_user_sessions(user_id)
            token = await db.auth.create_session(user_id)
            return user, token

    async def delete_user(self, user_id: int) -> None:
        try:
            async with self._database_factory() as db:
                user = await db.user.get_user_by_id(user_id)
                if user is None:
                    raise NotFoundError("User not found")
                if user.enabled and await db.user.enabled_count() <= 1:
                    raise ConflictError("Cannot delete the last enabled user")
                await db.auth.purge_user_credentials(user_id)
                if not await db.user.delete_user(user_id):
                    raise NotFoundError("User not found")
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc

    async def create_api_token_for_username(
        self,
        username: str,
        *,
        name: str,
        scope: str,
        expires_at: datetime | None = None,
    ) -> tuple[ApiToken, str]:
        async with self._database_factory() as db:
            user = await db.user.find_user(username)
            if user is None:
                raise NotFoundError("User not found")
            return await db.auth.create_api_token(
                self._user_id(user),
                name=name,
                scope=scope,
                expires_at=expires_at,
            )

    async def list_api_tokens(self) -> list[ApiToken]:
        async with self._database_factory() as db:
            return await db.auth.list_api_tokens()

    async def revoke_api_token(self, token_id: int) -> None:
        async with self._database_factory() as db:
            if not await db.auth.revoke_api_token(token_id):
                raise NotFoundError("API token not found")

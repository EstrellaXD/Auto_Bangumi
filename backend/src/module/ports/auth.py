"""Protocols required by authentication application services."""

from datetime import datetime, timedelta
from types import TracebackType
from typing import Protocol, Self

from module.models.auth import ApiToken
from module.models.user import User, UserUpdate


class UserRepository(Protocol):
    async def authenticate_credentials(
        self, username: str, password: str
    ) -> User | None: ...

    async def find_user(self, username: str) -> User | None: ...

    async def list_users(self) -> list[User]: ...

    async def create_user(self, username: str, password: str) -> User: ...

    async def update_user_by_id(
        self, user_id: int, data: UserUpdate, *, commit: bool = True
    ) -> User: ...

    async def delete_user(self, user_id: int, *, commit: bool = True) -> bool: ...

    async def get_user_by_id(self, user_id: int) -> User | None: ...

    async def enabled_count(self) -> int: ...


class SessionTokenRepository(Protocol):
    async def create_session(self, user_id: int, *, commit: bool = True) -> str: ...

    async def authenticate_session(self, raw_token: str) -> User | None: ...

    async def refresh_session(
        self, raw_token: str, *, ttl: timedelta
    ) -> User | None: ...

    async def revoke_session(self, raw_token: str) -> bool: ...

    async def revoke_user_sessions(
        self, user_id: int, *, commit: bool = True
    ) -> int: ...

    async def create_api_token(
        self,
        user_id: int,
        *,
        name: str,
        scope: str,
        expires_at: datetime | None = None,
    ) -> tuple[ApiToken, str]: ...

    async def authenticate_api_token(
        self, raw_token: str, *, scope: str
    ) -> tuple[User, int] | None: ...

    async def touch_api_token(self, token_id: int) -> None: ...

    async def list_api_tokens(self) -> list[ApiToken]: ...

    async def revoke_api_token(self, token_id: int) -> bool: ...

    async def passkey_belongs_to_user(
        self, user_id: int, credential_id: str
    ) -> bool: ...

    async def purge_user_credentials(
        self, user_id: int, *, commit: bool = True
    ) -> None: ...


class AuthUnitOfWork(Protocol):
    @property
    def user(self) -> UserRepository: ...

    @property
    def auth(self) -> SessionTokenRepository: ...

    async def begin_write(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

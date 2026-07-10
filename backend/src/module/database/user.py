import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from module.models import ResponseModel
from module.models.user import User, UserUpdate
from module.security.jwt import get_password_hash, verify_password

logger = logging.getLogger(__name__)


class UserDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, username: str) -> User:
        statement = select(User).where(User.username == username)
        result = await self.session.execute(statement)
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def find_user(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    async def authenticate_credentials(
        self, username: str, password: str
    ) -> User | None:
        user = await self.find_user(username)
        if (
            user is None
            or not user.enabled
            or not verify_password(password, user.password)
        ):
            return None
        return user

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def list_users(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(col(User.username)))
        return list(result.scalars().all())

    async def create_user(self, username: str, password: str) -> User:
        if await self.find_user(username) is not None:
            raise ValueError("Username already exists")
        user = User(username=username, password=get_password_hash(password))
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("Username already exists") from exc
        await self.session.refresh(user)
        return user

    async def _enabled_count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(col(User.enabled).is_(True))
        )
        return int(result.scalar_one())

    async def enabled_count(self) -> int:
        return await self._enabled_count()

    async def update_user_by_id(self, user_id: int, data: UserUpdate) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        if data.enabled is False and user.enabled and await self._enabled_count() <= 1:
            raise ValueError("Cannot disable the last enabled user")
        if data.username is not None and data.username != user.username:
            if await self.find_user(data.username) is not None:
                raise ValueError("Username already exists")
            user.username = data.username
        if data.password is not None:
            user.password = get_password_hash(data.password)
        if data.enabled is not None:
            user.enabled = data.enabled
        user.updated_at = datetime.now(timezone.utc)
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("Username already exists") from exc
        await self.session.refresh(user)
        return user

    async def set_enabled(self, user_id: int, enabled: bool) -> User:
        return await self.update_user_by_id(user_id, UserUpdate(enabled=enabled))

    async def delete_user(self, user_id: int) -> bool:
        user = await self.session.get(User, user_id)
        if user is None:
            return False
        if user.enabled and await self._enabled_count() <= 1:
            raise ValueError("Cannot delete the last enabled user")
        await self.session.delete(user)
        await self.session.commit()
        return True

    async def auth_user(self, user: User) -> ResponseModel:
        statement = select(User).where(User.username == user.username)
        result = await self.session.execute(statement)
        db_user = result.scalars().first()
        if not user.password:
            return ResponseModel(
                status_code=401,
                status=False,
                msg_en="Incorrect password format",
                msg_zh="密码格式不正确",
            )
        if not db_user or not db_user.enabled:
            return ResponseModel(
                status_code=401,
                status=False,
                msg_en="User not found",
                msg_zh="用户不存在",
            )
        if not verify_password(user.password, db_user.password):
            return ResponseModel(
                status_code=401,
                status=False,
                msg_en="Incorrect password",
                msg_zh="密码错误",
            )
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en="Login successfully",
            msg_zh="登录成功",
        )

    async def update_user(self, username: str, update_user: UserUpdate) -> User:
        statement = select(User).where(User.username == username)
        result = await self.session.execute(statement)
        db_user = result.scalars().first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        if db_user.id is None:
            raise RuntimeError("Persisted user has no primary key")
        return await self.update_user_by_id(db_user.id, update_user)

    async def add_default_user(self):
        statement = select(User)
        try:
            result = await self.session.execute(statement)
            users = list(result.scalars().all())
        except Exception as e:
            # Table may not exist yet during initial setup
            logger.debug(f"Could not query users table (may not exist yet): {e}")
            users = []
        if len(users) != 0:
            return
        user = User(username="admin", password=get_password_hash("adminadmin"))
        self.session.add(user)
        await self.session.commit()
        logger.info("Created default admin user")

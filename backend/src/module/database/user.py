import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from module.models import ResponseModel
from module.models.user import User, UserLogin, UserUpdate
from module.security.jwt import get_password_hash, verify_password

logger = logging.getLogger(__name__)


class UserDatabase:
    def __init__(self, session):
        self.session = session

    async def get_user(self, username):
        statement = select(User).where(User.username == username)
        if isinstance(self.session, AsyncSession):
            result = await self.session.execute(statement)
            user = result.scalar_one_or_none()
        else:
            user = self.session.exec(statement).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def auth_user(self, user: User):
        statement = select(User).where(User.username == user.username)
        if isinstance(self.session, AsyncSession):
            result = await self.session.execute(statement)
            db_user = result.scalar_one_or_none()
        else:
            db_user = self.session.exec(statement).first()
        if not user.password:
            return ResponseModel(
                status_code=401, status=False, msg_en="Incorrect password format", msg_zh="密码格式不正确"
            )
        if not db_user:
            return ResponseModel(
                status_code=401, status=False, msg_en="User not found", msg_zh="用户不存在"
            )
        if not verify_password(user.password, db_user.password):
            return ResponseModel(
                status_code=401,
                status=False,
                msg_en="Incorrect password",
                msg_zh="密码错误",
            )
        return ResponseModel(
            status_code=200, status=True, msg_en="Login successfully", msg_zh="登录成功"
        )

    async def update_user(self, username, update_user: UserUpdate):
        statement = select(User).where(User.username == username)
        if isinstance(self.session, AsyncSession):
            result = await self.session.execute(statement)
            db_user = result.scalar_one_or_none()
        else:
            db_user = self.session.exec(statement).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        if update_user.username:
            db_user.username = update_user.username
        if update_user.password:
            db_user.password = get_password_hash(update_user.password)
        self.session.add(db_user)
        if isinstance(self.session, AsyncSession):
            await self.session.commit()
        else:
            self.session.commit()
        return db_user

    async def add_default_user(self):
        statement = select(User)
        if isinstance(self.session, AsyncSession):
            result = await self.session.execute(statement)
            users = list(result.scalars().all())
        else:
            try:
                users = self.session.exec(statement).all()
            except Exception:
                self.merge_old_user()
                users = self.session.exec(statement).all()
        if len(users) != 0:
            return
        user = User(username="admin", password=get_password_hash("adminadmin"))
        self.session.add(user)
        if isinstance(self.session, AsyncSession):
            await self.session.commit()
        else:
            self.session.commit()

    def merge_old_user(self):
        # Legacy migration - sync only
        statement = """
        SELECT * FROM user
        """
        result = self.session.exec(statement).first()
        if not result:
            return
        user = User(username=result.username, password=result.password)
        statement = """
        DROP TABLE user
        """
        self.session.exec(statement)
        statement = """
        CREATE TABLE user (
            id INTEGER NOT NULL PRIMARY KEY,
            username VARCHAR NOT NULL,
            password VARCHAR NOT NULL
        )
        """
        self.session.exec(statement)
        self.session.add(user)
        self.session.commit()

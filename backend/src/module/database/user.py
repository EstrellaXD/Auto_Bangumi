import logging

from fastapi import HTTPException
from sqlmodel import Session, select

from models.user import User, UserUpdate
from module.security.jwt import get_password_hash

logger = logging.getLogger(__name__)


class UserDatabase:
    def __init__(self, session: Session):
        self.session:Session = session

    def get_user(self, username) -> User | None:
        statement = select(User).where(User.username == username)
        result = self.session.exec(statement).first()
        return result

    def auth_user(self, user: User) -> bool:
        statement = select(User).where(User.username == user.username)
        result = self.session.exec(statement).first()
        if not result:
            return False
        return True

    def update_user(self, username, update_user: UserUpdate):
        # Update username and password
        statement = select(User).where(User.username == username)
        result = self.session.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        if update_user.username:
            result.username = update_user.username
        if update_user.password:
            result.password = get_password_hash(update_user.password)
        self.session.add(result)
        self.session.commit()
        return result


    def add_default_user(self):
        # Check if user exists
        statement = select(User)
        result = self.session.exec(statement).all()
        if len(result) != 0:
            return
        # Add default user
        user = User(username="admin", password=get_password_hash("adminadmin"))
        self.session.add(user)
        self.session.commit()

import logging

from fastapi import HTTPException

from module.models.user import User, UserUpdate, UserLogin
from module.security.jwt import get_password_hash, verify_password
from module.database.engine import engine
from sqlmodel import Session, select, SQLModel

logger = logging.getLogger(__name__)


class AuthDB(Session):
    def __init__(self):
        super().__init__()
        self.__update_table()

    @staticmethod
    def __update_table():
        SQLModel.metadata.create_all(engine)

    # @staticmethod
    # def __data_to_db(data: User) -> dict:
    #     db_data = data.dict()
    #     db_data["password"] = get_password_hash(db_data["password"])
    #     return db_data
    #
    # @staticmethod
    # def __db_to_data(db_data: dict) -> User:
    #     return User(**db_data)

    def get_user(self, username):
        statement = select(User).where(User.username == username)
        result = self.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        return result

    def auth_user(self, user: UserLogin) -> bool:
        statement = select(User).where(User.username == user.username)
        result = self.exec(statement).first()
        if not result:
            raise HTTPException(status_code=401, detail="User not found")
        if not verify_password(user.password, result.password):
            raise HTTPException(status_code=401, detail="Password error")
        return True

    def update_user(self, username, update_user: UserUpdate):
        # Update username and password
        statement = select(User).where(User.username == username)
        result = self.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        if update_user.username:
            result.username = update_user.username
        if update_user.password:
            result.password = get_password_hash(update_user.password)
        self.add(result)
        self.commit()
        return result


if __name__ == "__main__":
    with AuthDB() as db:
        # db.update_user(UserLogin(username="admin", password="adminadmin"), User(username="admin", password="cica1234"))
        db.update_user("admin", User(username="estrella", password="cica1234"))

import logging

from fastapi import HTTPException

from module.database.connector import DataConnector

from module.security.jwt import get_password_hash, verify_password
from module.models.user import User

logger = logging.getLogger(__name__)


class AuthDB(DataConnector):
    def __init__(self):
        super().__init__()
        self.__table_name = "user"
        if not self._table_exists(self.__table_name):
            self.__update_table()

    def __update_table(self):
        db_data = self.__data_to_db(User())
        self._update_table(self.__table_name, db_data)
        self._insert(self.__table_name, db_data)

    @staticmethod
    def __data_to_db(data: User) -> dict:
        db_data = data.dict()
        db_data["password"] = get_password_hash(db_data["password"])
        return db_data

    @staticmethod
    def __db_to_data(db_data: dict) -> User:
        return User(**db_data)

    def get_user(self, username):
        self._cursor.execute(
            f"SELECT * FROM {self.__table_name} WHERE username=?", (username,)
        )
        result = self._cursor.fetchone()
        if not result:
            return None
        db_data = dict(zip([x[0] for x in self._cursor.description], result))
        return self.__db_to_data(db_data)

    def auth_user(self, username, password) -> bool:
        self._cursor.execute(
            f"SELECT username, password FROM {self.__table_name} WHERE username=?",
            (username,),
        )
        result = self._cursor.fetchone()
        if not result:
            raise HTTPException(status_code=401, detail="User not found")
        if not verify_password(password, result[1]):
            raise HTTPException(status_code=401, detail="Password error")
        return True

    def update_user(self, username, update_user: User):
        # Update username and password
        new_username = update_user.username
        new_password = update_user.password
        self._cursor.execute(
            f"""
            UPDATE {self.__table_name}
            SET username = '{new_username}', password = '{get_password_hash(new_password)}'
            WHERE username = '{username}'
        """
        )
        self._conn.commit()


if __name__ == "__main__":
    with AuthDB() as db:
        # db.update_user(UserLogin(username="admin", password="adminadmin"), User(username="admin", password="cica1234"))
        db.update_user("admin", User(username="estrella", password="cica1234"))

from fastapi import HTTPException

from .connector import DataConnector

from module.security.jwt import get_password_hash, verify_password
from module.models import UserLogin


class AuthDB(DataConnector):
    def update_table(self):
        pass

    def auth_user(self, user: UserLogin) -> bool:
        username = user.username
        password = user.password
        self._cursor.execute(f"SELECT * FROM user WHERE username='{username}'")
        result = self._cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        if not verify_password(password, result[2]):
            raise HTTPException(status_code=401, detail="Password error")
        return True

    def update_user(self, user: UserUpdate):
        # Update username and password
        username = user.username
        new_username = user.new_username
        password = user.password
        new_password = user.new_password
        self._cursor.execute(f"SELECT * FROM user WHERE username='{username}'")
        result = self._cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        if not verify_password(password, result[2]):
            raise HTTPException(status_code=401, detail="Password error")
        self._cursor.execute("""
            UPDATE user
            SET username=%s, password=%s
            WHERE username=%s
            """, (new_username, get_password_hash(new_password), username))
        self._conn.commit()
        return True

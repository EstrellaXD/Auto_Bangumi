import sqlite3

from .delete import Delete
from .insert import Insert
from .select import Select
from .update import Update

from module.conf import DATA_PATH


class Connector:
    def __init__(self, database: str = DATA_PATH, table_name: str = None, data: dict = None):
        self._conn = sqlite3.connect(database)
        self._cursor = self._conn.cursor()
        self.update = Update(self, table_name, data)
        self.insert = Insert(self, table_name, data)
        self.select = Select(self, table_name, data)
        self.delete = Delete(self, table_name, data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._conn.close()

    def execute(self, sql: str, params: tuple = None):
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, params)
        self._conn.commit()

    def executemany(self, sql: str, params: list[tuple]):
        self._cursor.executemany(sql, params)
        self._conn.commit()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchmany(self, size: int):
        return self._cursor.fetchmany(size)
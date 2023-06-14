import sqlite3

from .delete import Delete
from .insert import Insert
from .select import Select
from .update import Update

from module.conf import DATA_PATH


class Connector:
    def __init__(self, table_name: str, data: dict, database: str = DATA_PATH):
        self._conn = sqlite3.connect(database)
        self._cursor = self._conn.cursor()
        self.update = Update(self, table_name, data)
        self.insert = Insert(self, table_name, data)
        self.select = Select(self, table_name, data)
        self.delete = Delete(self, table_name, data)
        self._columns = self.__get_columns(table_name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._conn.close()

    def __get_columns(self, table_name: str) -> list[str]:
        self._cursor.execute(f"PRAGMA table_info({table_name})")
        return [x[1] for x in self._cursor.fetchall()]

    def execute(self, sql: str, params: tuple = None):
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, params)
        self._conn.commit()

    def executemany(self, sql: str, params: list[tuple]):
        self._cursor.executemany(sql, params)
        self._conn.commit()

    def fetchall(self) -> dict:
        datas = self._cursor.fetchall()
        for data in datas:
            yield dict(zip(self._columns, data))

    def fetchone(self):
        return dict(zip(self._columns, self._cursor.fetchone()))

    def fetchmany(self, size: int):
        datas = self._cursor.fetchmany(size)
        for data in datas:
            yield dict(zip(self._columns, data))

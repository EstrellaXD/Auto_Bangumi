import os
import sqlite3
import logging

from module.conf import DATA_PATH

logger = logging.getLogger(__name__)


class DataConnector:
    def __init__(self):
        # Create folder if not exists
        if not os.path.exists(os.path.dirname(DATA_PATH)):
            os.makedirs(os.path.dirname(DATA_PATH))
        self._conn = sqlite3.connect(DATA_PATH)
        self._cursor = self._conn.cursor()

    def _update_table(self, table_name: str, db_data: dict):
        columns = ", ".join([f"{key} {self.__python_to_sqlite_type(value)}" for key, value in db_data.items()])
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns});"
        self._cursor.execute(create_table_sql)
        self._cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {column_info[1]: column_info for column_info in self._cursor.fetchall()}
        for key, value in db_data.items():
            if key not in existing_columns:
                add_column_sql = f"ALTER TABLE {table_name} ADD COLUMN {key} {self.__python_to_sqlite_type(value)} DEFAULT {value};"
                self._cursor.execute(add_column_sql)
        self._conn.commit()
        logger.debug(f"Create / Update table {table_name}.")

    def _insert(self, table_name: str,  db_data: dict):
        columns = ", ".join(db_data.keys())
        values = ", ".join([f":{key}" for key in db_data.keys()])
        self._cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES ({values})", db_data)
        self._conn.commit()

    def _insert_list(self, table_name: str, data_list: list[dict]):
        columns = ", ".join(data_list[0].keys())
        values = ", ".join([f":{key}" for key in data_list[0].keys()])
        self._cursor.executemany(f"INSERT INTO {table_name} ({columns}) VALUES ({values})", data_list)
        self._conn.commit()

    def _delete_all(self, table_name: str):
        self._cursor.execute(f"DELETE FROM {table_name}")
        self._conn.commit()

    @staticmethod
    def __python_to_sqlite_type(value) -> str:
        if isinstance(value, int):
            return "INTEGER NOT NULL"
        elif isinstance(value, float):
            return "REAL NOT NULL"
        elif isinstance(value, str):
            return "TEXT NOT NULL"
        elif isinstance(value, bool):
            return "INTEGER NOT NULL"
        elif isinstance(value, list):
            return "TEXT NOT NULL"
        elif value is None:
            return "TEXT"
        else:
            raise ValueError(f"Unsupported data type: {type(value)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._conn.close()

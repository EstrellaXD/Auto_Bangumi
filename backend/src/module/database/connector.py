import logging
import os
import sqlite3

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
        columns = ", ".join(
            [
                f"{key} {self.__python_to_sqlite_type(value)}"
                for key, value in db_data.items()
            ]
        )
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns});"
        self._cursor.execute(create_table_sql)
        self._cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {
            column_info[1]: column_info for column_info in self._cursor.fetchall()
        }
        for key, value in db_data.items():
            if key not in existing_columns:
                insert_column = self.__python_to_sqlite_type(value)
                if value is None:
                    value = "NULL"
                add_column_sql = f"ALTER TABLE {table_name} ADD COLUMN {key} {insert_column} DEFAULT {value};"
                self._cursor.execute(add_column_sql)
        self._conn.commit()
        logger.debug(f"Create / Update table {table_name}.")

    def _insert(self, table_name: str, db_data: dict):
        columns = ", ".join(db_data.keys())
        values = ", ".join([f":{key}" for key in db_data.keys()])
        self._cursor.execute(
            f"INSERT INTO {table_name} ({columns}) VALUES ({values})", db_data
        )
        self._conn.commit()

    def _insert_list(self, table_name: str, data_list: list[dict]):
        columns = ", ".join(data_list[0].keys())
        values = ", ".join([f":{key}" for key in data_list[0].keys()])
        self._cursor.executemany(
            f"INSERT INTO {table_name} ({columns}) VALUES ({values})", data_list
        )
        self._conn.commit()

    def _select(self, keys: list[str], table_name: str, condition: str = None) -> dict:
        if condition is None:
            self._cursor.execute(f"SELECT {', '.join(keys)} FROM {table_name}")
        else:
            self._cursor.execute(
                f"SELECT {', '.join(keys)} FROM {table_name} WHERE {condition}"
            )
        return dict(zip(keys, self._cursor.fetchone()))

    def _update(self, table_name: str, db_data: dict):
        _id = db_data.get("id")
        if _id is None:
            raise ValueError("No _id in db_data.")
        set_sql = ", ".join([f"{key} = :{key}" for key in db_data.keys()])
        self._cursor.execute(
            f"UPDATE {table_name} SET {set_sql} WHERE id = {_id}", db_data
        )
        self._conn.commit()
        return self._cursor.rowcount == 1

    def _update_list(self, table_name: str, data_list: list[dict]):
        if len(data_list) == 0:
            return
        set_sql = ", ".join(
            [f"{key} = :{key}" for key in data_list[0].keys() if key != "id"]
        )
        self._cursor.executemany(
            f"UPDATE {table_name} SET {set_sql} WHERE id = :id", data_list
        )
        self._conn.commit()

    def _update_section(self, table_name: str, location: dict, update_dict: dict):
        set_sql = ", ".join([f"{key} = :{key}" for key in update_dict.keys()])
        sql_loc = f"{location['key']} = {location['value']}"
        self._cursor.execute(
            f"UPDATE {table_name} SET {set_sql} WHERE {sql_loc}", update_dict
        )
        self._conn.commit()

    
    def _delete_all(self, table_name: str):
        self._cursor.execute(f"DELETE FROM {table_name}")
        self._conn.commit()

    
    def _search_data(self, table_name: str, keys: list[str] | None, condition: str) -> dict:
        if keys is None:
            self._cursor.execute(f"SELECT * FROM {table_name} WHERE {condition}")
        else:
            self._cursor.execute(
                f"SELECT {', '.join(keys)} FROM {table_name} WHERE {condition}"
            )
        return dict(zip(keys, self._cursor.fetchone()))

    
    def _search_datas(self, table_name: str, keys: list[str] | None, condition: str = None) -> list[dict]:
        if keys is None:
            select_sql = "*"
        else:
            select_sql = ", ".join(keys)
        if condition is None:
            self._cursor.execute(f"SELECT {select_sql} FROM {table_name}")
        else:
            self._cursor.execute(
                f"SELECT {select_sql} FROM {table_name} WHERE {condition}"
            )
        return [dict(zip(keys, row)) for row in self._cursor.fetchall()]

    def _table_exists(self, table_name: str) -> bool:
        self._cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table_name,),
        )
        return len(self._cursor.fetchall()) == 1

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

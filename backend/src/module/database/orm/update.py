import logging
from .connector import Connector

logger = logging.getLogger(__name__)


class Update:
    def __init__(self, db: Connector, table_name: str, data: dict):
        self.db = db
        self._table_name = table_name
        self._columns = data.items()

    def table(self):
        columns = ", ".join(
            [
                f"{key} {self.__python_to_sqlite_type(value)}"
                for key, value in self._columns
            ]
        )
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {self._table_name} ({columns});"
        self.db.execute(create_table_sql)
        self.db.execute(f"PRAGMA table_info({self._table_name})")
        existing_columns = {
            column_info[1]: column_info for column_info in self.db.fetchall()
        }
        for key, value in self._columns:
            if key not in existing_columns:
                insert_column = self.__python_to_sqlite_type(value)
                if value is None:
                    value = "NULL"
                add_column_sql = f"ALTER TABLE {self._table_name} ADD COLUMN {key} {insert_column} DEFAULT {value};"
                self.db.execute(add_column_sql)
        logger.debug(f"Create / Update table {self._table_name}.")

    def one(self, data: dict) -> bool:
        _id = data.pop("id")
        set_sql = ", ".join([f"{key} = :{key}" for key in data.keys()])
        self.db.execute(
            f"""
            UPDATE {self._table_name}
            SET {set_sql}
            WHERE id = {_id}
            """,
            data,
        )
        logger.debug(f"Update {_id} in {self._table_name}.")
        return True

    def list(self, data: list[dict]):
        for item in data:
            self.one(item)

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
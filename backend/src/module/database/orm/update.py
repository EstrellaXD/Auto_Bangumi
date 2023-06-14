import logging

logger = logging.getLogger(__name__)


class Update:
    def __init__(self, connector, table_name: str, data: dict):
        self._connector = connector
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
        self._connector.execute(create_table_sql)
        self._connector.execute(f"PRAGMA table_info({self._table_name})")
        existing_columns = {
            column_info[1]: column_info for column_info in self._connector.fetchall()
        }
        for key, value in self._columns:
            if key not in existing_columns:
                insert_column = self.__python_to_sqlite_type(value)
                if value is None:
                    value = "NULL"
                add_column_sql = f"ALTER TABLE {self._table_name} ADD COLUMN {key} {insert_column} DEFAULT {value};"
                self._connector.execute(add_column_sql)
        logger.debug(f"Create / Update table {self._table_name}.")

    def one(self, data: dict) -> bool:
        _id = data["id"]
        set_sql = ", ".join([f"{key} = :{key}" for key in data.keys()])
        self._connector.execute(
            f"""
            UPDATE {self._table_name}
            SET {set_sql}
            WHERE id = :id
            """,
            data,
        )
        logger.debug(f"Update {_id} in {self._table_name}.")
        return True

    def many(self, data: list[dict]) -> bool:
        columns = ", ".join(data[0].keys())
        self._connector.executemany(
            f"""
            UPDATE {self._table_name}
            SET {columns}
            WHERE id = :id
            """,
            data,
        )
        logger.debug(f"Update {self._table_name}.")
        return True

    def value(self, location: dict, set_value: dict) -> bool:
        set_sql = ", ".join([f"{key} = :{key}" for key in set_value.keys()])
        params = {**location, **set_value}
        self._connector.execute(
            f"""
            UPDATE {self._table_name}
            SET {set_sql}
            WHERE {location["key"]} = :{location["key"]}
            """,
            params,
        )
        logger.debug(f"Update {self._table_name}.")
        return True

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

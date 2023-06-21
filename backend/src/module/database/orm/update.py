import logging

logger = logging.getLogger(__name__)


class Update:
    def __init__(self, connector, table_name: str, data: dict):
        self._connector = connector
        self._table_name = table_name
        self._example_data = data

    def __table_exists(self) -> bool:
        self._connector.execute(
            f"""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='{self._table_name}'
            """
        )
        return self._connector.fetch() is not None

    def table(self):
        columns_list = [
            self.__python_to_sqlite_type(key, value)
            for key, value in self._example_data.items()
        ]
        columns = ", ".join(columns_list)
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {self._table_name} ({columns});"
        self._connector.execute(create_table_sql)
        logger.debug(f"Create table {self._table_name}.")
        self._connector.execute(f"PRAGMA table_info({self._table_name})")
        existing_columns = [x[1] for x in self._connector.fetch()]
        for key, value in self._example_data.items():
            if key not in existing_columns:
                insert_column = self.__python_to_sqlite_type(key, value)
                if value is None:
                    value = "NULL"
                add_column_sql = f"ALTER TABLE {self._table_name} ADD COLUMN {insert_column} DEFAULT {value};"
                self._connector.execute(add_column_sql)
                logger.debug(f"Update table {self._table_name}.")

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
        columns = ", ".join([f"{key} = :{key}" for key in data[0].keys()])
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
    def __python_to_sqlite_type(key, value) -> str:
        if key == "id":
            column = "INTEGER PRIMARY KEY"
        elif isinstance(value, int):
            column = "INTEGER NOT NULL"
        elif isinstance(value, float):
            column = "REAL NOT NULL"
        elif isinstance(value, str):
            column = "TEXT NOT NULL"
        elif isinstance(value, bool):
            column = "INTEGER NOT NULL"
        elif isinstance(value, list):
            column = "TEXT NOT NULL"
        elif value is None:
            column = "TEXT"
        else:
            raise ValueError(f"Unsupported data type: {type(value)}")
        return f"{key} {column}"

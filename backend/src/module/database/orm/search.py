
class Select:
    def __init__(self, connector: Connector, table_name: str, data: dict):
        self._connector = connector
        self._table_name = table_name
        self._data = data

    def id(self, _id: int):
        self._connector.execute(
            f"""
            SELECT * FROM {self._table_name}
            WHERE id = :id
            """,
            {"id": _id},
        )
        return self._connector.fetchone()

    def all(self):
        self._connector.execute(
            f"""
            SELECT * FROM {self._table_name}
            """,
        )
        return self._connector.fetchall()

    def one(self, keys: list[str], values: list[str]):
        columns = ", ".join(keys)
        placeholders = ", ".join([f":{key}" for key in keys])
        self._connector.execute(
            f"""
            SELECT {columns} FROM {self._table_name}
            WHERE {placeholders}
            """,
            dict(zip(keys, values)),
        )
        return self._connector.fetchone()

    def list(self, keys: list[str], values: list[str]):
        columns = ", ".join(keys)
        placeholders = ", ".join([f":{key}" for key in keys])
        self._connector.execute(
            f"""
            SELECT {columns} FROM {self._table_name}
            WHERE {placeholders}
            """,
            dict(zip(keys, values)),
        )
        return self._connector.fetchall()
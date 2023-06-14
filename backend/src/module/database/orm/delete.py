class Delete:
    def __init__(self, connector, table_name: str, data: dict):
        self._connector = connector
        self._table_name = table_name
        self._data = data

    def one(self, _id: int) -> bool:
        self._connector.execute(
            f"""
            DELETE FROM {self._table_name}
            WHERE id = :id
            """,
            {"id": _id},
        )
        return True

    def all(self):
        self._connector.execute(
            f"""
            DELETE FROM {self._table_name}
            """,
        )
        return True

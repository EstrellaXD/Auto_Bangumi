

class Delete:
    def __init__(self, connector: Connector, table_name: str, data: dict):
        self.db = connector
        self._table_name = table_name
        self._data = data

    def one(self, _id: int) -> bool:
        self.db.execute(
            f"""
            DELETE FROM {self._table_name}
            WHERE id = :id
            """,
            {"id": _id},
        )
        return True

    def all(self):
        self.db.execute(
            f"""
            DELETE FROM {self._table_name}
            """,
        )
        return True


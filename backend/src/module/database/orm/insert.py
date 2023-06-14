class Insert:
    def __init__(self, connector, table_name: str, data: dict):
        self._connector = connector
        self._table_name = table_name
        self._columns = data.items()

    def __gen_id(self) -> int:
        self._connector.execute(f"SELECT MAX(id) FROM {self._table_name}")
        max_id = self._connector.fetchone()[0]
        if max_id is None:
            return 1
        return max_id + 1

    def one(self, data: dict):
        if data["id"] is not None:
            raise ValueError("id must be None")
        _id = self.__gen_id()
        data["id"] = _id
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{key}" for key in data.keys()])
        self._connector.execute(
            f"""
            INSERT INTO {self._table_name} ({columns})
            VALUES ({placeholders})
            """,
            data,
        )

    def many(self, data: list[dict]):
        for item in data:
            self.one(item)

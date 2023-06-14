from .connector import Connector


class Insert:
    def __init__(self, db: Connector, table_name: str, data: dict):
        self.db = db
        self._table_name = table_name
        self._columns = data.items()

    def __gen_id(self) -> int:
        self.db.execute(f"SELECT MAX(id) FROM {self._table_name}")
        max_id = self.db.fetchone()[0]
        if max_id is None:
            return 1
        return max_id + 1

    def one(self, data: dict) -> bool:
        _id = self.__gen_id()
        data["id"] = _id
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{key}" for key in data.keys()])
        self.db.execute(
            f"""
            INSERT INTO {self._table_name} ({columns})
            VALUES ({placeholders})
            """,
            data,
        )
        return True

    def list(self, data: list[dict]):
        columns = ", ".join(data[0].keys())
        placeholders = ", ".join([f":{key}" for key in data[0].keys()])
        self.db.executemany(
            f"""
            INSERT INTO {self._table_name} ({columns})
            VALUES ({placeholders})
            """,
            data,
        )
        return True



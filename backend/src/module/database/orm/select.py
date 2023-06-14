class Select:
    def __init__(self, connector, table_name: str, data: dict):
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

    def all(self, limit: int = None):
        if limit is None:
            limit = 10000
        self._connector.execute(
            f"""
            SELECT * FROM {self._table_name} LIMIT {limit}
            """,
        )
        return self._connector.fetchall()

    def one(
        self,
        keys: list[str] | None = None,
        conditions: dict = None,
        combine_operator: str = "AND",
    ):
        if keys is None:
            keys = ["*"]
        columns = ", ".join(keys)

        self._connector.execute(
            f"""
            SELECT {columns} FROM {self._table_name}
            WHERE {condition_sql}
            """,
            conditions,
        )
        return self._connector.fetchone()

    def many(
        self,
        keys: list[str] | None = None,
        conditions: dict = None,
        combine_operator: str = "AND",
        limit: int = None,
    ):
        if keys is None:
            keys = ["*"]
        if limit is None:
            limit = 10000
        columns = ", ".join(keys)
        condition_sql = self.__select_condition(conditions, combine_operator)
        self._connector.execute(
            f"""
            SELECT {columns} FROM {self._table_name}
            WHERE {condition_sql}
            LIMIT {limit}
            """,
            conditions,
        )
        return self._connector.fetchall()

    def column(self, keys: list[str]):
        columns = ", ".join(keys)
        self._connector.execute(
            f"""
            SELECT {columns} FROM {self._table_name}
            """,
        )
        return self._connector.fetchall()

    @staticmethod
    def __select_condition(conditions: dict, combine_operator: str = "AND"):
        if not conditions:
            raise ValueError("No conditions provided.")
        if combine_operator not in ["AND", "OR", "INSTR"]:
            raise ValueError("Invalid combine_operator, must be 'AND' or 'OR'.")
        if combine_operator == "INSTR":
            condition_sql = f" {combine_operator} {' AND '.join([f'({key} = :{key})' for key in conditions.keys()])}"
        else:
            condition_sql = f" {combine_operator} ".join(
                [f"{key} = :{key}" for key in conditions.keys()]
            )
        return condition_sql

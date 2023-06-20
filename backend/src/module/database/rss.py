from .orm import Connector

from module.models import RSSItem
from module.conf import DATA_PATH


class RSSDatabase(Connector):
    def __init__(self, database: str = DATA_PATH):
        super().__init__(
            table_name="RSSItem",
            data=RSSItem().dict(),
            database=database
        )

    @staticmethod
    def __data_to_db(data: RSSItem) -> dict:
        db_data = data.dict()
        for key, value in db_data.items():
            if isinstance(value, bool):
                db_data[key] = int(value)
            elif isinstance(value, list):
                db_data[key] = ",".join(value)
        return db_data

    @staticmethod
    def __db_to_data(db_data: dict) -> RSSItem:
        for key, item in db_data.items():
            if isinstance(item, int):
                db_data[key] = bool(item)
        return RSSItem(**db_data)

    def update_table(self):
        self.update.table()

    def insert_one(self, data: RSSItem):
        dict_data = self.__data_to_db(data)
        self.insert.one(data=dict_data)

    def get_all(self) -> list[RSSItem]:
        dict_datas = self.select.all()
        return [self.__db_to_data(x) for x in dict_datas]

    def delete_one(self, _id: int):
        self.delete.one(_id)

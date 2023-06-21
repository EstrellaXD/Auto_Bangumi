import logging

from module.database.orm import Connector
from module.models import TorrentData
from module.conf import DATA_PATH

logger = logging.getLogger(__name__)


class TorrentDatabase(Connector):
    def __init__(self, database: str = DATA_PATH):
        super().__init__(
            table_name="torrent", data=TorrentData().dict(), database=database
        )

    def update_table(self):
        self.update.table()

    def __data_to_db(self, data: TorrentData) -> dict:
        db_data = data.dict()
        for key, value in db_data.items():
            if isinstance(value, bool):
                db_data[key] = int(value)
            elif isinstance(value, list):
                db_data[key] = ",".join(value)
        return db_data

    def __db_to_data(self, db_data: dict) -> TorrentData:
        for key, item in db_data.items():
            if isinstance(item, int):
                db_data[key] = bool(item)
            elif key in ["filter", "rss_link"]:
                db_data[key] = item.split(",")
        return TorrentData(**db_data)

    def insert_many(self, data_list: list[TorrentData]):
        dict_datas = [self.__data_to_db(data) for data in data_list]
        self.insert.many(dict_datas)

    def get_all(self) -> list[TorrentData]:
        dict_datas = self.select.all()
        return [self.__db_to_data(data) for data in dict_datas]

    def get_torrent_name(self) -> list[str]:
        dict_data = self.select.all()
        return [data["name"] for data in dict_data]


if __name__ == "__main__":
    with TorrentDatabase() as db:
        db.update_table()

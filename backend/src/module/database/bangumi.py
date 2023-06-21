import logging

from module.database.orm import Connector
from module.models import BangumiData
from module.conf import DATA_PATH

logger = logging.getLogger(__name__)


class BangumiDatabase(Connector):
    def __init__(self, database: str = DATA_PATH):
        super().__init__(
            table_name="bangumi",
            data=self.__data_to_db(BangumiData()),
            database=database,
        )

    def update_table(self):
        self.update.table()

    @staticmethod
    def __data_to_db(data: BangumiData) -> dict:
        db_data = data.dict()
        for key, value in db_data.items():
            if isinstance(value, bool):
                db_data[key] = int(value)
            elif isinstance(value, list):
                db_data[key] = ",".join(value)
        return db_data

    @staticmethod
    def __db_to_data(db_data: dict) -> BangumiData:
        for key, item in db_data.items():
            if isinstance(item, int):
                if key not in ["id", "offset", "season", "year"]:
                    db_data[key] = bool(item)
            elif key in ["filter", "rss_link"]:
                db_data[key] = item.split(",")
        return BangumiData(**db_data)

    def insert_one(self, data: BangumiData):
        db_data = self.__data_to_db(data)
        self.insert.one(db_data)
        logger.debug(f"[Database] Insert {data.official_title} into database.")
        # if self.__check_exist(data):
        #     self.update_one(data)
        # else:
        #     db_data = self.__data_to_db(data)
        #     db_data["id"] = self.gen_id()
        #     self._insert(db_data=db_data, table_name=self.__table_name)
        #     logger.debug(f"[Database] Insert {data.official_title} into database.")

    def insert_list(self, data: list[BangumiData]):
        data_list = [self.__data_to_db(x) for x in data]
        self.insert.many(data_list)
        # _id = self.gen_id()
        # for i, item in enumerate(data):
        #     item.id = _id + i
        # data_list = [self.__data_to_db(x) for x in data]
        # self._insert_list(data_list=data_list, table_name=self.__table_name)
        logger.debug(f"[Database] Insert {len(data)} bangumi into database.")

    def update_one(self, data: BangumiData) -> bool:
        db_data = self.__data_to_db(data)
        return self.update.one(db_data)

    def update_list(self, data: list[BangumiData]):
        data_list = [self.__data_to_db(x) for x in data]
        self.update.many(data_list)

    def update_rss(self, title_raw, rss_set: str):
        # Update rss and added
        location = {"title_raw": title_raw}
        set_value = {"rss_link": rss_set, "added": 0}
        self.update.value(location, set_value)
        # self._cursor.execute(
        #     """
        #     UPDATE bangumi
        #     SET rss_link = :rss_link, added = 0
        #     WHERE title_raw = :title_raw
        #     """,
        #     {"rss_link": rss_set, "title_raw": title_raw},
        # )
        # self._conn.commit()
        logger.debug(f"[Database] Update {title_raw} rss_link to {rss_set}.")

    def update_poster(self, title_raw, poster_link: str):
        location = {"title_raw": title_raw}
        set_value = {"poster_link": poster_link}
        self.update.value(location, set_value)
        logger.debug(f"[Database] Update {title_raw} poster_link to {poster_link}.")

    def delete_one(self, _id: int):
        self.delete.one(_id)
        logger.debug(f"[Database] Delete bangumi id: {_id}.")

    def delete_all(self):
        self.delete.all()

    def search_all(self) -> list[BangumiData]:
        all_data = self.select.all()
        return [self.__db_to_data(x) for x in all_data]

    def search_id(self, _id: int) -> BangumiData | None:
        dict_data = self.select.one(conditions={"id": _id})
        if dict_data is None:
            logger.warning(f"[Database] Cannot find bangumi id: {_id}.")
            return None
        logger.debug(f"[Database] Find bangumi id: {_id}.")
        return self.__db_to_data(dict_data)

    # def search_official_title(self, official_title: str) -> BangumiData | None:
    #     dict_data = self._search_data(
    #         table_name=self.__table_name, condition={"official_title": official_title}
    #     )
    #     if dict_data is None:
    #         return None
    #     return self.__db_to_data(dict_data)

    def match_poster(self, bangumi_name: str) -> str:
        condition = {"official_title": bangumi_name}
        keys = ["poster_link"]
        data = self.select.one(
            keys=keys,
            conditions=condition,
            combine_operator="INSTR",
        )
        if not data:
            return ""
        return data.get("poster_link")

    def match_list(self, torrent_list: list, rss_link: str) -> list:
        # Match title_raw in database
        keys = ["title_raw", "rss_link", "poster_link"]
        match_datas = self.select.column(keys)
        if not match_datas:
            return torrent_list
        # Match title
        i = 0
        while i < len(torrent_list):
            torrent = torrent_list[i]
            for match_data in match_datas:
                if match_data.get("title_raw") in torrent.name:
                    if rss_link not in match_data.get("rss_link"):
                        match_data["rss_link"] += f",{rss_link}"
                        self.update_rss(
                            match_data.get("title_raw"), match_data.get("rss_link")
                        )
                    if not match_data.get("poster_link"):
                        self.update_poster(
                            match_data.get("title_raw"), torrent.poster_link
                        )
                    torrent_list.pop(i)
                    break
            else:
                i += 1
        return torrent_list

    def not_complete(self) -> list[BangumiData]:
        # Find eps_complete = False
        condition = {"eps_collect": 0}
        dict_data = self.select.many(
            conditions=condition,
        )
        return [self.__db_to_data(x) for x in dict_data]

    def not_added(self) -> list[BangumiData]:
        conditions = {"added": 0, "rule_name": None, "save_path": None}
        dict_data = self.select.many(conditions=conditions, combine_operator="OR")
        return [self.__db_to_data(x) for x in dict_data]

    def get_rss(self, rss_link: str) -> list[BangumiData]:
        conditions = {"rss_link": rss_link}
        dict_data = self.select.many(conditions=conditions, combine_operator="INSTR")
        return [self.__db_to_data(x) for x in dict_data]

    def match_torrent(self, torrent_name: str, rss_link: str) -> BangumiData | None:
        conditions = {"title_raw": torrent_name, "rss_link": rss_link}
        dict_data = self.select.one(conditions=conditions, combine_operator="INSTR")
        if not dict_data:
            return None
        return self.__db_to_data(dict_data)


if __name__ == "__main__":
    with BangumiDatabase() as db:
        db.match_torrent(
            "魔法科高校の劣等生 来訪者編", "https://bangumi.moe/rss/5f6b3e3e4e8c4b0001b2e3a3"
        )

import logging

from module.database.connector import DataConnector
from module.models import BangumiData

logger = logging.getLogger(__name__)


class BangumiDatabase(DataConnector):
    def __init__(self):
        super().__init__()

    def update_table(self):
        table_name = "bangumi"
        db_data = self.__data_to_db(BangumiData())
        self._update_table(table_name, db_data)

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

    def __fetch_data(self) -> list[BangumiData]:
        values = self._cursor.fetchall()
        if values is None:
            return []
        keys = [x[0] for x in self._cursor.description]
        dict_data = [dict(zip(keys, value)) for value in values]
        return [self.__db_to_data(x) for x in dict_data]

    def insert(self, data: BangumiData):
        db_data = self.__data_to_db(data)
        columns = ", ".join(db_data.keys())
        values = ", ".join([f":{key}" for key in db_data.keys()])
        self._cursor.execute(f"INSERT INTO bangumi ({columns}) VALUES ({values})", db_data)
        logger.debug(f"Add {data.official_title} into database.")
        self._conn.commit()

    def insert_list(self, data: list[BangumiData]):
        db_data = [self.__data_to_db(x) for x in data]
        columns = ", ".join(db_data[0].keys())
        values = ", ".join([f":{key}" for key in db_data[0].keys()])
        self._cursor.executemany(f"INSERT INTO bangumi ({columns}) VALUES ({values})", db_data)
        logger.debug(f"Add {len(data)} bangumi into database.")
        self._conn.commit()

    def update_one(self, data: BangumiData) -> bool:
        db_data = self.__data_to_db(data)
        update_columns = ", ".join([f"{key} = :{key}" for key in db_data.keys() if key != "id"])
        self._cursor.execute(f"UPDATE bangumi SET {update_columns} WHERE id = :id", db_data)
        self._conn.commit()
        return self._cursor.rowcount == 1

    def update_list(self, data: list[BangumiData]):
        db_data = [self.__data_to_db(x) for x in data]
        update_columns = ", ".join([f"{key} = :{key}" for key in db_data[0].keys() if key != "id"])
        self._cursor.executemany(f"UPDATE bangumi SET {update_columns} WHERE id = :id", db_data)
        self._conn.commit()

    def update_rss(self, title_raw, rss_set: str):
        # Update rss and added
        self._cursor.execute(
            """
            UPDATE bangumi 
            SET rss_link = :rss_link, added = 0
            WHERE title_raw = :title_raw
            """,
            {"rss_link": rss_set, "title_raw": title_raw},
        )
        self._conn.commit()
        logger.debug(f"Update {title_raw} rss_link to {rss_set}.")

    def delete_one(self, _id: int) -> bool:
        self._cursor.execute(
            """
            DELETE FROM bangumi WHERE id = :id
            """,
            {"id": _id},
        )
        self._conn.commit()
        logger.debug(f"Delete bangumi id: {_id}.")
        return self._cursor.rowcount == 1

    def delete_all(self):
        self._cursor.execute(
            """
            DELETE FROM bangumi
            """
        )
        self._conn.commit()
        logger.debug("Delete all bangumi.")

    def search_all(self) -> list[BangumiData]:
        self._cursor.execute(
            """
            SELECT * FROM bangumi
            """
        )
        return self.__fetch_data()

    def search_id(self, _id: int) -> BangumiData | None:
        self._cursor.execute(
            """
            SELECT * FROM bangumi WHERE id = :id
            """,
            {"id": _id},
        )
        values = self._cursor.fetchone()
        if values is None:
            return None
        keys = [x[0] for x in self._cursor.description]
        dict_data = dict(zip(keys, values))
        return self.__db_to_data(dict_data)

    def search_official_title(self, official_title: str) -> BangumiData | None:
        self._cursor.execute(
            """
            SELECT * FROM bangumi WHERE official_title = :official_title
            """,
            {"official_title": official_title},
        )
        values = self._cursor.fetchone()
        if values is None:
            return None
        keys = [x[0] for x in self._cursor.description]
        dict_data = dict(zip(keys, values))
        return self.__db_to_data(dict_data)

    def match_poster(self, bangumi_name: str) -> str:
        # Find title_raw which in torrent_name
        self._cursor.execute(
            """
            SELECT official_title, poster_link FROM bangumi
            """
        )
        data = self._cursor.fetchall()
        if not data:
            return ""
        for official_title, poster_link in data:
            if official_title in bangumi_name:
                if poster_link:
                    return poster_link
        return ""

    def match_list(self, torrent_list: list, rss_link: str) -> list:
        # Match title_raw in database
        self._cursor.execute(
            """
            SELECT title_raw, rss_link FROM bangumi
            """
        )
        data = self._cursor.fetchall()
        if not data:
            return torrent_list
        # Match title
        i = 0
        while i < len(torrent_list):
            torrent = torrent_list[i]
            for title_raw, rss_set in data:
                if title_raw in torrent.name:
                    if rss_link not in rss_set:
                        rss_set += "," + rss_link
                        self.update_rss(title_raw, rss_set)
                    torrent_list.pop(i)
                    break
            else:
                i += 1
        return torrent_list

    def not_complete(self) -> list[BangumiData]:
        # Find eps_complete = False
        self._cursor.execute(
            """
            SELECT * FROM bangumi WHERE eps_collect = 0
            """
        )
        return self.__fetch_data()

    def not_added(self) -> list[BangumiData]:
        self._cursor.execute(
            """
            SELECT * FROM bangumi WHERE added = 0
            """
        )
        return self.__fetch_data()

    def gen_id(self) -> int:
        self._cursor.execute(
            """
            SELECT id FROM bangumi ORDER BY id DESC LIMIT 1
            """
        )
        data = self._cursor.fetchone()
        if data is None:
            return 1
        return data[0] + 1


if __name__ == '__main__':
    title = "[SweetSub&LoliHouse] Heavenly Delusion - 06 [WebRip 1080p HEVC-10bit AAC ASSx2].mkv"
    with BangumiDatabase() as db:
        print(db.match_poster(title))
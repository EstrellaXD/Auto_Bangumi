import logging

from .connector import DataConnector

logger = logging.getLogger(__name__)

class TorrentDatabase(DataConnector):

    def update_table(self):
        table_name = "torrent"
        db_data = self.__data_to_db()
        self._update_table(table_name, db_data)

    def __data_to_db(self, data: SaveTorrent):
        db_data = data.dict()
        for key, value in db_data.items():
            if isinstance(value, bool):
                db_data[key] = int(value)
            elif isinstance(value, list):
                db_data[key] = ",".join(value)
        return db_data

    def __db_to_data(self, db_data: dict):
        for key, item in db_data.items():
            if isinstance(item, int):
                if key not in ["id", "offset", "season", "year"]:
                    db_data[key] = bool(item)
            elif key in ["filter", "rss_link"]:
                db_data[key] = item.split(",")
        return SaveTorrent(**db_data)

    def if_downloaded(self, torrent_url: str, torrent_name: str) -> bool:
        self._cursor.execute("SELECT * FROM torrent WHERE torrent_url = ? OR torrent_name = ?",
                                (torrent_url, torrent_name))
        return bool(self._cursor.fetchone())

    def insert(self, data: SaveTorrent):
        db_data = self.__data_to_db(data)
        columns = ", ".join(db_data.keys())
        values = ", ".join([f":{key}" for key in db_data.keys()])
        self._cursor.execute(f"INSERT INTO torrent ({columns}) VALUES ({values})", db_data)
        logger.debug(f"Add {data.torrent_name} into database.")
        self._conn.commit()
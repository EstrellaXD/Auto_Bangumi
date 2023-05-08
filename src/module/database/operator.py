import logging

from module.database.connector import DataConnector
from module.models import BangumiData

logger = logging.getLogger(__name__)


class DataOperator(DataConnector):
    @staticmethod
    def data_to_db(data: BangumiData) -> dict:
        db_data = data.dict()
        for key, value in db_data.items():
            if isinstance(value, bool):
                db_data[key] = int(value)
            elif isinstance(value, list):
                db_data[key] = ",".join(value)
        return db_data

    @staticmethod
    def db_to_data(db_data: dict) -> BangumiData:
        for key, item in db_data.items():
            if isinstance(item, int):
                if key not in ["id", "offset", "season"]:
                    db_data[key] = bool(item)
            elif key in ["filter", "rss_link"]:
                db_data[key] = item.split(",")
        return BangumiData(**db_data)

    def insert(self, data: BangumiData):
        db_data = self.data_to_db(data)
        self._cursor.execute(
            """
            INSERT INTO bangumi (
                id,
                official_title,
                year,
                title_raw,
                season,
                season_raw,
                group_name,
                dpi,
                source,
                subtitle,
                eps_collect,
                offset,
                filter,
                rss_link
                ) VALUES (
                :id,
                :official_title,
                :year,
                :title_raw,
                :season,
                :season_raw,
                :group,
                :dpi,
                :source,
                :subtitle,
                :eps_collect,
                :offset,
                :filter,
                :rss_link
                )
                """,
            db_data,
        )
        logger.debug(f"Add {data.official_title} into database.")
        self._conn.commit()

    def insert_list(self, data: list[BangumiData]):
        db_data = [self.data_to_db(x) for x in data]
        self._cursor.executemany(
            """
            INSERT INTO bangumi (
                id,
                official_title,
                year,
                title_raw,
                season,
                season_raw,
                group_name,
                dpi,
                source,
                subtitle,
                eps_collect,
                offset,
                filter,
                rss_link
                ) VALUES (
                :id,
                :official_title,
                :year,
                :title_raw,
                :season,
                :season_raw,
                :group,
                :dpi,
                :source,
                :subtitle,
                :eps_collect,
                :offset,
                :filter,
                :rss_link
                )
                """,
            db_data,
        )
        self._conn.commit()

    def update(self, data: BangumiData) -> bool:
        db_data = self.data_to_db(data)
        self._cursor.execute(
            """
            UPDATE bangumi SET
                official_title = :official_title,
                year = :year,
                title_raw = :title_raw,
                season = :season,
                season_raw = :season_raw,
                group_name = :group,
                dpi = :dpi,
                source = :source,
                subtitle = :subtitle,
                eps_collect = :eps_collect,
                offset = :offset,
                filter = :filter,
                rss_link = :rss_link
            WHERE id = :id
            """,
            db_data,
        )
        self._conn.commit()
        return self._cursor.rowcount == 1

    def update_rss(self, title_raw, rss_set: list[str]):
        self._cursor.execute(
            """
            UPDATE bangumi SET
                rss_link = :rss_link
            WHERE title_raw = :title_raw
            """,
            {"rss_link": ",".join(rss_set), "title_raw": title_raw},
        )
        self._conn.commit()
        logger.info(f"Update {title_raw} rss_link to {rss_set}.")
        return self._cursor.rowcount == 1

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
        return self.db_to_data(dict_data)

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
        return self.db_to_data(dict_data)

    def match_official_title(self, title: str) -> bool:
        self._cursor.execute(
            """
            SELECT official_title FROM bangumi 
            WHERE official_title = :official_title
            """,
            {"official_title": title},
        )
        return self._cursor.fetchone() is not None

    def match_title_raw(self, title: str, rss_link: str) -> bool:
        self._cursor.execute(
            """
            SELECT title_raw, rss_link FROM bangumi 
            WHERE INSTR (:title_raw, title_raw) > 0 AND INSTR (:rss_link, rss_link) > 0
            """,
            {"title_raw": title, "rss_link": rss_link},
        )
        return self._cursor.fetchone() is not None

    def match_list(self, title_dict: dict) -> dict:
        # Match title_raw in database
        self._cursor.execute(
            """
            SELECT title_raw, rss_link FROM bangumi
            """
        )
        data = self._cursor.fetchall()
        if not data:
            return {}
        # Match title
        for title, rss_link in title_dict.items():
            for title_raw, rss_set in data:
                if rss_link in rss_set and title_raw in title:
                    del title_dict[title]
                elif rss_link not in rss_set and title_raw in title:
                    # TODO: Logic problem
                break
        return title_dict

    def not_exist_titles(self, titles: list[str], rss_link) -> list[str]:
        # Select all title in titles that title_raw in database not in title
        self._cursor.execute(
            """
            SELECT title_raw, rss_link FROM bangumi
            """
        )
        data = self._cursor.fetchall()
        if not data:
            return titles
        # Match title
        for title_raw, rss_set in data:
            rss_set = rss_set.split(",")
            for title in titles:
                if rss_link in rss_set:
                    if title_raw in title:
                        titles.remove(title)
                elif rss_link not in rss_set:
                    rss_set.append(rss_link)
                    self.update_rss(title_raw, rss_set)
        return titles

    def get_to_complete(self) -> list[BangumiData] | None:
        # Find eps_complete = False
        self._cursor.execute(
            """
            SELECT * FROM bangumi WHERE eps_collect = 1
            """
        )
        values = self._cursor.fetchall()
        if values is None:
            return None
        keys = [x[0] for x in self._cursor.description]
        dict_data = [dict(zip(keys, value)) for value in values]
        return [self.db_to_data(x) for x in dict_data]

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
    with DataOperator() as op:
        datas = op.get_to_complete()
        _id = op.gen_id()
        for data in datas:
            print(data)
        print(_id)
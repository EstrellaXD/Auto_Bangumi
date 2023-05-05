from module.database.connector import DataConnector


from module.models import BangumiData


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
            elif key in ["filter", "rss"]:
                db_data[key] = item.split(",")
        return BangumiData(**db_data)

    def insert(self, data: BangumiData):
        db_data = self.data_to_db(data)
        self._cursor.execute('''
            INSERT INTO bangumi (
                id,
                official_title,
                title_raw,
                season,
                season_raw,
                subtitle,
                group_name,
                source,
                dpi,
                eps_collect,
                offset,
                filter,
                rss
                ) VALUES (
                :id,
                :official_title,
                :title_raw,
                :season,
                :season_raw,
                :subtitle,
                :group,
                :source,
                :dpi,
                :eps_collect,
                :offset,
                :filter,
                :rss
                )
                ''', db_data)
        self._conn.commit()

    def insert_list(self, data: list[BangumiData]):
        db_data = [self.data_to_db(x) for x in data]
        self._cursor.executemany('''
            INSERT INTO bangumi (
                id,
                official_title,
                title_raw,
                season,
                season_raw,
                subtitle,
                group_name,
                source,
                dpi,
                eps_collect,
                offset,
                filter,
                rss
                ) VALUES (
                :id,
                :official_title,
                :title_raw,
                :season,
                :season_raw,
                :subtitle,
                :group,
                :source,
                :dpi,
                :eps_collect,
                :offset,
                :filter,
                :rss
                )
                ''', db_data)
        self._conn.commit()

    def update(self, data: BangumiData) -> bool:
        db_data = self.data_to_db(data)
        self._cursor.execute('''
            UPDATE bangumi SET
                official_title = :official_title,
                title_raw = :title_raw,
                season = :season,
                season_raw = :season_raw,
                subtitle = :subtitle,
                group_name = :group,
                source = :source,
                dpi = :dpi,
                eps_collect = :eps_collect,
                offset = :offset,
                filter = :filter
            WHERE id = :id
            ''', db_data)
        self._conn.commit()
        return self._cursor.rowcount == 1

    def search_id(self, _id: int) -> BangumiData | None:
        self._cursor.execute('''
            SELECT * FROM bangumi WHERE id = :id
            ''', {"id": _id})
        values = self._cursor.fetchone()
        if values is None:
            return None
        keys = [x[0] for x in self._cursor.description]
        dict_data = dict(zip(keys, values))
        return self.db_to_data(dict_data)

    def search_official_title(self, official_title: str) -> BangumiData | None:
        self._cursor.execute('''
            SELECT * FROM bangumi WHERE official_title = :official_title
            ''', {"official_title": official_title})
        values = self._cursor.fetchone()
        if values is None:
            return None
        keys = [x[0] for x in self._cursor.description]
        dict_data = dict(zip(keys, values))
        return self.db_to_data(dict_data)

    def match_title(self, title: str) -> bool:
        # Select all title_raw
        self._cursor.execute('''
            SELECT title_raw FROM bangumi
            ''')
        title_raws = [x[0] for x in self._cursor.fetchall()]
        # Match title
        for title_raw in title_raws:
            if title_raw in title:
                return True
        return False

    def not_exist_titles(self, titles: list[str]) -> list[str]:
        # Select all title_raw
        self._cursor.execute('''
            SELECT title_raw FROM bangumi
            ''')
        title_raws = [x[0] for x in self._cursor.fetchall()]
        # Match title
        for title_raw in title_raws:
            for title in titles:
                if title_raw in title:
                    titles.remove(title)
        return titles

    def gen_id(self) -> int:
        self._cursor.execute('''
            SELECT id FROM bangumi ORDER BY id DESC LIMIT 1
            ''')
        return self._cursor.fetchone()[0] + 1


if __name__ == '__main__':
    with DataOperator() as op:
        pass


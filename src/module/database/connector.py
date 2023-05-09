import os
import sqlite3


from module.conf import DATA_PATH


class DataConnector:
    def __init__(self):
        if not os.path.isfile(DATA_PATH):
            os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        self._conn = sqlite3.connect(DATA_PATH)
        self._cursor = self._conn.cursor()
        self._cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bangumi (
                id INTEGER PRIMARY KEY,
                official_title TEXT NOT NULL,
                year INTEGER,
                title_raw TEXT NOT NULL,
                season INTEGER NOT NULL,
                season_raw TEXT NOT NULL,
                group_name TEXT,
                dpi TEXT,
                source TEXT,
                subtitle TEXT,
                eps_collect INTEGER NOT NULL,
                offset INTEGER NOT NULL,
                filter TEXT NOT NULL,
                rss_link TEXT NOT NULL,
                poster_link TEXT,
                added INTEGER NOT NULL
            );
            """
        )
        self._conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._conn.close()

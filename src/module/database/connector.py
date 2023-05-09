import os
import sqlite3


from module.conf import DATA_PATH


class DataConnector:
    def __init__(self):
        if not os.path.isfile(DATA_PATH):
            os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        self._conn = sqlite3.connect(DATA_PATH)
        self._cursor = self._conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._conn.close()

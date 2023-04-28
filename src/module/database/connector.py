from sqlite3 import Cursor


from module.conf import settings, DATA_PATH


class DataConnector:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


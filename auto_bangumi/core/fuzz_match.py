from thefuzz import fuzz


# TODO 模糊匹配模块


class FuzzMatch:
    def __init__(self, anidb_data):
        self.match_data = anidb_data

    def fuzz(self, raw_name):
        fuzz.radio()
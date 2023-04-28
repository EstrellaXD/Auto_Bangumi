from .connector import DataConnector


from module.models import BangumiData


class DataOperator(DataConnector):
    def insert(self, data: BangumiData):
        pass

    def insert_list(self, data: list[BangumiData]):
        pass

    def update(self, data: BangumiData) -> bool:
        pass

    def search(self, id: int) -> bool:
        pass



    def match_title(self, title: str) -> bool:
        return False

    def gen_id(self) -> int:
        return 1


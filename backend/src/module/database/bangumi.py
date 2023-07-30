import logging

from module.database.orm import Connector
from module.models import Bangumi, BangumiUpdate
from module.conf import DATA_PATH
from sqlmodel import Session, select, delete, SQLModel
from module.database.engine import engine
from typing import Optional
from sqlalchemy.exc import IntegrityError, NoResultFound

logger = logging.getLogger(__name__)


class BangumiDatabase(Session):
    def __init__(self):
        super().__init__(engine)
        #     table_name="bangumi",
        #     data=self.__data_to_db(BangumiData()),
        #     database=database,
        # )

    @staticmethod
    def update_table():
        SQLModel.metadata.create_all(engine)

    # @staticmethod
    # def __data_to_db(data: BangumiData) -> Bangumi:
    #     db_data = data.dict()
    #     for key, value in db_data.items():
    #         if isinstance(value, bool):
    #             db_data[key] = int(value)
    #         elif isinstance(value, list):
    #             db_data[key] = ",".join(value)
    #     return db_data
    #
    # @staticmethod
    # def __db_to_data(db_data: Bangumi) -> BangumiData:
    #     for key, item in db_data.items():
    #         if isinstance(item, int):
    #             if key not in ["id", "offset", "season", "year"]:
    #                 db_data[key] = bool(item)
    #         elif key in ["filter", "rss_link"]:
    #             db_data[key] = item.split(",")
    #     return BangumiData(**db_data)

    def insert_one(self, data: Bangumi):
        self.add(data)
        self.commit()
        # db_data = self.__data_to_db(data)
        # self.insert.one(db_data)
        logger.debug(f"[Database] Insert {data.official_title} into database.")

    def insert_list(self, data: list[Bangumi]):
        self.add_all(data)
        # data_list = [self.__data_to_db(x) for x in data]
        # self.insert.many(data_list)
        # _id = self.gen_id()
        # for i, item in enumerate(data):
        #     item.id = _id + i
        # data_list = [self.__data_to_db(x) for x in data]
        # self._insert_list(data_list=data_list, table_name=self.__table_name)
        logger.debug(f"[Database] Insert {len(data)} bangumi into database.")

    def update_one(self, data: BangumiUpdate) -> bool:
        db_data = self.get(Bangumi, data.id)
        if not db_data:
            return False
        bangumi_data = data.dict(exclude_unset=True)
        for key, value in bangumi_data.items():
            setattr(db_data, key, value)
        self.add(db_data)
        self.commit()
        self.refresh(db_data)
        logger.debug(f"[Database] Update {data.official_title}")
        return True

    def update_list(self, datas: list[BangumiUpdate]):
        for data in datas:
            self.update_one(data)

    def update_rss(self, title_raw, rss_set: str):
        # Update rss and added
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        bangumi = self.exec(statement).first()
        bangumi.rss_link = rss_set
        bangumi.added = 0
        self.add(bangumi)
        self.commit()
        self.refresh(bangumi)
        # location = {"title_raw": title_raw}
        # set_value = {"rss_link": rss_set, "added": 0}
        # self.update.value(location, set_value)
        logger.debug(f"[Database] Update {title_raw} rss_link to {rss_set}.")

    def update_poster(self, title_raw, poster_link: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        bangumi = self.exec(statement).first()
        bangumi.poster_link = poster_link
        self.add(bangumi)
        self.commit()
        self.refresh(bangumi)
        logger.debug(f"[Database] Update {title_raw} poster_link to {poster_link}.")

    def delete_one(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        bangumi = self.exec(statement).first()
        self.delete(bangumi)
        self.commit()
        logger.debug(f"[Database] Delete bangumi id: {_id}.")

    def delete_all(self):
        statement = delete(Bangumi)
        self.exec(statement)
        self.commit()

    def search_all(self) -> list[Bangumi]:
        statement = select(Bangumi)
        return self.exec(statement).all()

    def search_id(self, _id: int) -> Optional[Bangumi]:
        statement = select(Bangumi).where(Bangumi.id == _id)
        bangumi = self.exec(statement).first()
        if bangumi is None:
            logger.warning(f"[Database] Cannot find bangumi id: {_id}.")
            return None
        else:
            logger.debug(f"[Database] Find bangumi id: {_id}.")
            return self.exec(statement).first()

    def match_poster(self, bangumi_name: str) -> str:
        # condition = {"official_title": bangumi_name}
        statement = select(Bangumi).where(Bangumi.official_title == bangumi_name)
        # keys = ["poster_link"]
        # data = self.select.one(
        #     keys=keys,
        #     conditions=condition,
        #     combine_operator="INSTR",
        # )
        data = self.exec(statement).first()
        if data:
            return data.poster_link
        else:
            return ""

    def match_list(self, torrent_list: list, rss_link: str) -> list:
        # Match title_raw in database
        # keys = ["title_raw", "rss_link", "poster_link"]
        # match_datas = self.select.column(keys)
        match_datas = self.search_all()
        if not match_datas:
            return torrent_list
        # Match title
        i = 0
        while i < len(torrent_list):
            torrent = torrent_list[i]
            for match_data in match_datas:
                if match_data.title_raw in torrent.name:
                    if rss_link not in match_data.rss_link:
                        match_data.rss_link += f",{rss_link}"
                        self.update_rss(
                            match_data.title_raw, match_data.rss_link
                        )
                    if not match_data.poster_link:
                        self.update_poster(
                            match_data.title_raw, torrent.poster_link
                        )
                    torrent_list.pop(i)
                    break
            else:
                i += 1
        return torrent_list

    def not_complete(self) -> list[Bangumi]:
        # Find eps_complete = False
        condition = select(Bangumi).where(Bangumi.eps_collect == 0)
        datas = self.exec(condition).all()
        return datas

    def not_added(self) -> list[Bangumi]:
        conditions = select(Bangumi).where(
            Bangumi.added == 0 or
            Bangumi.rule_name is None or
            Bangumi.save_path is None
            )
        datas = self.exec(conditions).all()
        # dict_data = self.select.many(conditions=conditions, combine_operator="OR")
        return datas


if __name__ == "__main__":
    with BangumiDatabase() as db:
        print(db.not_complete())

import logging

from sqlalchemy.sql import func
from sqlmodel import Session, and_, delete, false, or_, select

from module.models import Bangumi, BangumiUpdate
from module.models.torrent import Torrent

logger = logging.getLogger(__name__)


class BangumiDatabase:
    def __init__(self, session: Session):
        self.session = session

    def add(self, data: Bangumi):
        """link 相同, official_title相同,就只补充,主要是为了
        一些会改名的

        Args:
            data: [TODO:description]

        Returns:
            [TODO:return]
        """
        # 如果official_title 一致,将title_raw,group,更新
        statement = select(Bangumi).where(
            and_(
                data.official_title==Bangumi.official_title ,
                func.instr(data.rss_link, Bangumi.rss_link) > 0,
                # use `false()` to avoid E712 checking
                # see: https://docs.astral.sh/ruff/rules/true-false-comparison/
                Bangumi.deleted == false(),
            )
        )
        bangumi = self.session.exec(statement).first()
        if bangumi:
            if data.title_raw in bangumi.title_raw:
                logger.debug(
                    f"[Database] {data.official_title} has inserted into database."
                )
                return False
            bangumi.title_raw += f",{data.title_raw}"
            data = bangumi
            logger.debug(
                f"[Database] update {data.official_title}"
            )
         
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)
        logger.debug(f"[Database] Insert {data.official_title} into database.")
        return True

    def add_all(self, datas: list[Bangumi]):
        self.session.add_all(datas)
        self.session.commit()
        logger.debug(f"[Database] Insert {len(datas)} bangumi into database.")

    def update(self, data: Bangumi | BangumiUpdate, _id: int = None) -> bool:
        if _id and isinstance(data, BangumiUpdate):
            db_data = self.session.get(Bangumi, _id)
        elif isinstance(data, Bangumi):
            db_data = self.session.get(Bangumi, data.id)
        else:
            return False
        if not db_data:
            return False
        bangumi_data = data.dict(exclude_unset=True)
        for key, value in bangumi_data.items():
            setattr(db_data, key, value)
        self.session.add(db_data)
        self.session.commit()
        self.session.refresh(db_data)
        logger.debug(f"[Database] Update {data.official_title}")
        return True

    def update_all(self, datas: list[Bangumi]):
        self.session.add_all(datas)
        self.session.commit()
        logger.debug(f"[Database] Update {len(datas)} bangumi.")

    def update_rss(self, title_raw, rss_set: str):
        # Update rss and added
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)

        bangumi = self.session.exec(statement).first()
        if bangumi:
            bangumi.rss_link = rss_set
            bangumi.added = False
            self.session.add(bangumi)
            self.session.commit()
            self.session.refresh(bangumi)
            logger.debug(f"[Database] Update {title_raw} rss_link to {rss_set}.")
            return True
        logger.debug(f"[Database] Cannot update {title_raw} rss_link to {rss_set}.")
        return False

    def update_poster(self, title_raw, poster_link: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        bangumi = self.session.exec(statement).first()
        bangumi.poster_link = poster_link
        self.session.add(bangumi)
        self.session.commit()
        self.session.refresh(bangumi)
        logger.debug(f"[Database] Update {title_raw} poster_link to {poster_link}.")

    def delete_one(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        bangumi = self.session.exec(statement).first()
        self.session.delete(bangumi)
        self.session.commit()
        logger.debug(f"[Database] Delete bangumi id: {_id}.")

    def delete_all(self):
        statement = delete(Bangumi)
        self.session.exec(statement)
        self.session.commit()

    def search_all(self) -> list[Bangumi]:
        statement = select(Bangumi)
        return self.session.exec(statement).all()

    def search_url(self, rss_link: str) -> Bangumi | None:
        statement = select(Bangumi).where(Bangumi.rss_link == rss_link)
        bangumi = self.session.exec(statement).first()
        if bangumi is None:
            logger.warning(f"[Database] Cannot find bangumi link: {rss_link}.")
            return None
        else:
            logger.debug(f"[Database] Find bangumi id: {rss_link}.")
            return self.session.exec(statement).first()


    def search_id(self, _id: int) -> Bangumi | None:
        statement = select(Bangumi).where(Bangumi.id == _id)
        bangumi = self.session.exec(statement).first()
        if bangumi is None:
            logger.warning(f"[Database] Cannot find bangumi id: {_id}.")
            return None
        else:
            logger.debug(f"[Database] Find bangumi id: {_id}.")
            return self.session.exec(statement).first()

    def match_poster(self, bangumi_name: str) -> str:
        # Use like to match
        statement = select(Bangumi).where(
            func.instr(bangumi_name, Bangumi.official_title) > 0
        )
        data = self.session.exec(statement).first()
        if data and data.poster_link:
            return data.poster_link
        else:
            return ""

    def match_list(
        self, torrent_list: list[Torrent], rss_link: str, aggrated: bool = True
    ) -> list[Torrent]:
        """
        find torrent name not in bangumi
        """
        new_torrents = []
        match_datas = self.search_all()
        if not match_datas:
            return torrent_list
        for torrent in torrent_list:
            match_bangumi = self.match_torrent(torrent.name, rss_link, aggrated)
            # 同一个bangumi 但是却不是相同的 rss link, 这种情况将俩个bangumi分开更符合直觉
            if not match_bangumi:
                new_torrents.append(torrent)
        return new_torrents

    def match_torrent(
        self, torrent_name: str, rss_link: str, aggrated=True
    ) -> Bangumi | None:
        # 对于聚合而言, link, title_raw一致可认为是一个bangumi
        # 对于非聚合, link 一致就可认为是一个
        if aggrated:
            statement = select(Bangumi).where(
                and_(
                    func.instr(torrent_name, Bangumi.title_raw) > 0,
                    func.instr(rss_link, Bangumi.rss_link) > 0,
                    # use `false()` to avoid E712 checking
                    # see: https://docs.astral.sh/ruff/rules/true-false-comparison/
                    Bangumi.deleted == false(),
                )
            )
        else:
            statement = select(Bangumi).where(
                and_(
                    func.instr(Bangumi.rss_link, rss_link),
                    # use `false()` to avoid E712 checking
                    # see: https://docs.astral.sh/ruff/rules/true-false-comparison/
                    Bangumi.deleted == false(),
                )
            )
        return self.session.exec(statement).first()

    def not_complete(self) -> list[Bangumi]:
        # Find eps_complete = False
        # use `false()` to avoid E712 checking
        # see: https://docs.astral.sh/ruff/rules/true-false-comparison/
        condition = select(Bangumi).where(
            and_(Bangumi.eps_collect == false(), Bangumi.deleted == false())
        )
        datas = self.session.exec(condition).all()
        return datas

    def not_added(self) -> list[Bangumi]:
        conditions = select(Bangumi).where(
            or_(
                Bangumi.added == 0, Bangumi.rule_name is None, Bangumi.save_path is None
            )
        )
        datas = self.session.exec(conditions).all()
        return datas

    def disable_rule(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        bangumi = self.session.exec(statement).first()
        if bangumi:
            bangumi.deleted = True
            self.session.add(bangumi)
            self.session.commit()
            self.session.refresh(bangumi)
            logger.debug(f"[Database] Disable rule {bangumi.title_raw}.")

    def search_rss(self, rss_link: str) -> list[Bangumi]:
        statement = select(Bangumi).where(func.instr(rss_link, Bangumi.rss_link) > 0)
        return self.session.exec(statement).all()


if __name__ == "__main__":
    from module.database import Database, engine

    from module.models.bangumi import Bangumi

    with Database() as db:
        test = BangumiDatabase(db)
        bangumis = test.search_id(2)
        if bangumis:
            bangumis.official_title = "12"

    # print(bangumis)
    with Database() as db2:
        test2 = BangumiDatabase(db2)
        test2.add_all([bangumis])
        # test.delete_one()

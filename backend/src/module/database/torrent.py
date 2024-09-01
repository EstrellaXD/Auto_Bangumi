import logging

from sqlalchemy.sql import func
from sqlmodel import Session, delete, false, select, true

from module.models import Torrent

logger = logging.getLogger(__name__)


class TorrentDatabase:
    def __init__(self, session: Session):
        self.session = session

    def add(self, data: Torrent):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)
        logger.debug(f"Insert {data.name} in database.")

    def add_all(self, datas: list[Torrent]):
        unique_torrent = [
            data
            for data in datas
            if not self.session.query(Torrent).filter_by(url=data.url).first()
        ]
        self.session.add_all(unique_torrent)
        self.session.commit()
        logger.debug(f"Insert {len(datas)} torrents in database.")

    def update(self, data: Torrent):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)
        logger.debug(f"Update {data.name} in database.")

    def update_all(self, datas: list[Torrent]):
        self.session.add_all(datas)
        self.session.commit()

    def update_one_user(self, data: Torrent):
        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)
        logger.debug(f"Update {data.name} in database.")

    def search(self, _id: int) -> Torrent:
        return self.session.exec(select(Torrent).where(Torrent.id == _id)).first()

    def search_hash(self, _hash: str) -> Torrent | None:
        statement = select(Torrent).where(func.instr(Torrent.url, _hash) > 0)
        return self.session.exec(statement).first()

    def search_torrent(self, _hash,_name=None):
        torrent_item = self.search_hash(_hash)
        if not torrent_item and _name:
            torrent_item = self.search_name(_name)
        return torrent_item

    def search_name(self, name: str):
        statement = select(Torrent).where(Torrent.name == name)
        return self.session.exec(statement).first()

    def search_bangumi(self, bangumi_id: int):
        return self.session.exec(
            select(Torrent).where(Torrent.bangumi_id == bangumi_id)
        ).all()

    def search_all(self) -> list[Torrent]:
        return self.session.exec(select(Torrent)).all()

    def search_all_unrenamed(self) -> list[Torrent]:
        return self.session.exec(
            select(Torrent).where(Torrent.downloaded == false())
        ).all()

    def search_all_downloaded(self) -> list[Torrent]:
        return self.session.exec(
            select(Torrent).where(Torrent.downloaded == true())
        ).all()

    def search_rss(self, rss_id: int) -> list[Torrent]:
        return self.session.exec(select(Torrent).where(Torrent.rss_id == rss_id)).all()

    def check_new(self, torrents_list: list[Torrent]) -> list[Torrent]:
        new_torrents = []
        for torrent in torrents_list:
            torrent_item = self.search_torrent(torrent.url,torrent.name)
            if torrent_item and not torrent_item.downloaded:
                new_torrents.append(torrent)
        return new_torrents

    def delete(self, _id: int) -> bool:
        condition = delete(Torrent).where(Torrent.id == _id)
        try:
            self.session.exec(condition)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Delete RSS Item failed. Because: {e}")
            return False

if __name__ == "__main__":
    from module.database import Database, engine
    from module.models.bangumi import Bangumi

    name = "[ANi] 物语系列 第外季＆第怪季 - 06 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
    hash = "1ae27b047005e097b74b66e27c37610aa5a0f5a2"
    with Database() as db:
        t_name = db.torrent.search_name(name)
        t_hash = db.torrent.search_hash(hash)
        db.torrent.delete(t_hash.id)
        # print(f"{t_name=}")
        # print(f"{t_hash=}")

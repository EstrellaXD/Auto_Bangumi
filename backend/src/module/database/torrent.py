import logging

from sqlalchemy.sql import func
from sqlmodel import Session, delete, false, select, true

from module.models import Torrent, torrent
from module.utils import get_hash

logger = logging.getLogger(__name__)


class TorrentDatabase:
    def __init__(self, session: Session):
        self.session = session

    def add(self, data: Torrent):
        self.session.merge(data)
        self.session.commit()
        logger.debug(f"[TorrentDatabase] Insert {data.name=} {data.url=} in database.")

    def add_all(self, datas: list[Torrent]):
        for data in datas:
            self.session.merge(data)
        self.session.commit()
        logger.debug(f"Insert {len(datas)} torrents in database.")

    def update(self, data: Torrent):
        logger.debug(f"[TorrentDatabase] update {data.name} in database.")
        self.session.merge(data)
        self.session.commit()
        self.session.refresh(data)
        logger.debug(f"[TorrentDatabase] Update {data.name} in database success.")
        logger.debug(f"Update {data.name} in database.")

    # def update_all(self, datas: list[Torrent]):
    #     self.session.add_all(datas)
    #     self.session.commit()
    #
    # def update_one_user(self, data: Torrent):
    #     self.session.add(data)
    #     self.session.commit()
    #     self.session.refresh(data)
    #     logger.debug(f"Update {data.name} in database.")
    #
    def filter_by_bangumi(self, official_title: str, season: int, rss_link: str) -> list[Torrent]:
        """根据 Bangumi 的官方标题、季节和 RSS 链接过滤种子"""
        statement = select(Torrent).where(
            Torrent.bangumi_official_title == official_title,
            Torrent.bangumi_season == season,
            Torrent.rss_link == rss_link,
        )
        return list(self.session.exec(statement).all())

    def search_by_url(self, url: str) -> Torrent | None:
        return self.session.get(Torrent, ident=url)
        # return self.session.exec(select(Torrent).where(Torrent.url == url)).first()

    def search_by_duid(self, duid: str) -> Torrent | None:
        statement = select(Torrent).where(Torrent.download_uid == duid)
        return self.session.exec(statement).first()

    def search_bangumi(self, bangumi_id: int):
        return self.session.exec(
            select(Torrent).where(Torrent.bangumi_id == bangumi_id)
        ).all()

    def search_all(self) -> list[Torrent]:
        return list(self.session.exec(select(Torrent)).all())

    def search_all_unrenamed(self) -> list[Torrent]:
        return list(
            self.session.exec(select(Torrent).where(Torrent.renamed == false())).all()
        )

    def search_all_downloaded(self) -> list[Torrent]:
        torrents = self.session.exec(
            select(Torrent).where(Torrent.downloaded == true())
        ).all()
        return list(torrents)

    # def search_rss(self, rss_url: int) -> list[Torrent]:
    #     """根据RSS url查询所有种子"""
    #     torrents = self.session.exec(select(Torrent).where(Torrent.rss_link == rss_url)).all()
    #     return list(torrents)

    def check_new(self, torrents_list: list[Torrent]) -> list[Torrent]:
        new_torrents = []
        for torrent in torrents_list:
            torrent_item = self.search_by_url(torrent.url)
            if not torrent_item or not torrent_item.downloaded:
                new_torrents.append(torrent)
        return new_torrents

    def delete_by_url(self, url: str) -> bool:
        # 思考什么时候删除种子
        # 1. 当bangumi已经删除时, 如果删除,会在重命名的时候再次添加
        # 2. 当种子也删除时, 不会再次添加
        # 3. bangumi 删除有几种情况: 1. 有一个全清, 会刷新一次 2. 用户自已删除, 如果是聚合的, 会在下次
        # 刷新时再次添加, 如果是单独的, 会连着rss 一起删除
        stmt = select(Torrent).where(Torrent.url == url)
        torrent_item = self.session.exec(stmt).first()
        if torrent_item:
            self.session.delete(torrent_item)
            logger.debug(
                f"[TorrentDatabase] Delete torrent {torrent_item.name} by url: {url}."
            )
            self.session.commit()
            return True

    def delete_by_duid(self, duid: str) -> bool:
        stmt = select(Torrent).where(Torrent.download_uid == duid)
        torrent_item = self.session.exec(stmt).first()
        if torrent_item:
            self.session.delete(torrent_item)
            logger.debug(
                f"[TorrentDatabase] Delete torrent {torrent_item.name} by duid: {duid}."
            )
            self.session.commit()
            return True
        return False


if __name__ == "__main__":
    from module.database import Database, engine
    from module.models.bangumi import Bangumi

    name = "[ANi] 物语系列 第外季＆第怪季 - 06 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
    hash = "1ae27b047005e097b74b66e27c37610aa5a0f5a2"
    with Database() as db:
        # t_name = db.torrent.search_name(name)
        t_hash = db.torrent.search_by_duid(hash)
        if t_hash:
            db.torrent.delete_by_url(t_hash.url)
        # print(f"{t_name=}")
        # print(f"{t_hash=}")

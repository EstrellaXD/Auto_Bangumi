import logging

from sqlmodel import Session, false, select, true

from module.models import Torrent, bangumi

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

    def search_bangumi(self,bangumi_id:int):
        return self.session.exec(select(Torrent).where(Torrent.bangumi_id == bangumi_id)).all()

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
        old_torrents = self.search_all_downloaded()
        old_urls = [t.url for t in old_torrents]
        for torrent in torrents_list:
            if torrent.url not in old_urls:
                new_torrents.append(torrent)
        return new_torrents



if __name__ == "__main__":
    from module.database import Database,engine
    
    from module.models.bangumi import Bangumi

    with Database() as db:
        test = TorrentDatabase(db)
        bangumis = test.search (2)
        bangumis.downloaded = True
        test = bangumis

    print(bangumis)
    with Database() as db2:
        test2 = TorrentDatabase(db2)
        test2.add_all([bangumis])
        # test.delete_one()

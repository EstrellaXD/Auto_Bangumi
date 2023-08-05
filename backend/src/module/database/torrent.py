import logging

from sqlmodel import Session, select

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
        self.session.add_all(datas)
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

    def search_all(self) -> list[Torrent]:
        return self.session.exec(select(Torrent)).all()

    def check_new(self, torrents_list: list[Torrent]) -> list[Torrent]:
        new_torrents = []
        old_torrents = self.search_all()
        old_urls = [t.url for t in old_torrents]
        for torrent in torrents_list:
            if torrent.url not in old_urls:
                new_torrents.append(torrent)
        return new_torrents

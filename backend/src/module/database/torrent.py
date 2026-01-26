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
        logger.debug(f"Insert {data.name} in database.")

    def add_all(self, datas: list[Torrent]):
        self.session.add_all(datas)
        self.session.commit()
        logger.debug(f"Insert {len(datas)} torrents in database.")

    def update(self, data: Torrent):
        self.session.add(data)
        self.session.commit()
        logger.debug(f"Update {data.name} in database.")

    def update_all(self, datas: list[Torrent]):
        self.session.add_all(datas)
        self.session.commit()

    def update_one_user(self, data: Torrent):
        self.session.add(data)
        self.session.commit()
        logger.debug(f"Update {data.name} in database.")

    def search(self, _id: int) -> Torrent | None:
        result = self.session.execute(
            select(Torrent).where(Torrent.id == _id)
        )
        return result.scalar_one_or_none()

    def search_all(self) -> list[Torrent]:
        result = self.session.execute(select(Torrent))
        return list(result.scalars().all())

    def search_rss(self, rss_id: int) -> list[Torrent]:
        result = self.session.execute(
            select(Torrent).where(Torrent.rss_id == rss_id)
        )
        return list(result.scalars().all())

    def check_new(self, torrents_list: list[Torrent]) -> list[Torrent]:
        if not torrents_list:
            return []
        urls = [t.url for t in torrents_list]
        statement = select(Torrent.url).where(Torrent.url.in_(urls))
        result = self.session.execute(statement)
        existing_urls = set(result.scalars().all())
        return [t for t in torrents_list if t.url not in existing_urls]

    def search_by_qb_hash(self, qb_hash: str) -> Torrent | None:
        """Find torrent by qBittorrent hash."""
        result = self.session.execute(
            select(Torrent).where(Torrent.qb_hash == qb_hash)
        )
        return result.scalar_one_or_none()

    def search_by_url(self, url: str) -> Torrent | None:
        """Find torrent by URL."""
        result = self.session.execute(
            select(Torrent).where(Torrent.url == url)
        )
        return result.scalar_one_or_none()

    def update_qb_hash(self, torrent_id: int, qb_hash: str) -> bool:
        """Update the qb_hash for a torrent."""
        torrent = self.search(torrent_id)
        if torrent:
            torrent.qb_hash = qb_hash
            self.session.add(torrent)
            self.session.commit()
            logger.debug(f"Updated qb_hash for torrent {torrent_id}: {qb_hash}")
            return True
        return False

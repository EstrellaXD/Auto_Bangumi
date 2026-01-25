import logging
import time
from typing import Optional

from sqlalchemy.sql import func
from sqlmodel import Session, and_, delete, false, or_, select

from module.models import Bangumi, BangumiUpdate

logger = logging.getLogger(__name__)

# Module-level TTL cache for search_all results
_bangumi_cache: list[Bangumi] | None = None
_bangumi_cache_time: float = 0
_BANGUMI_CACHE_TTL: float = 60.0  # seconds


def _invalidate_bangumi_cache():
    global _bangumi_cache, _bangumi_cache_time
    _bangumi_cache = None
    _bangumi_cache_time = 0


class BangumiDatabase:
    def __init__(self, session: Session):
        self.session = session

    def add(self, data: Bangumi) -> bool:
        statement = select(Bangumi).where(Bangumi.title_raw == data.title_raw)
        result = self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            return False
        self.session.add(data)
        self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Insert {data.official_title} into database.")
        return True

    def add_all(self, datas: list[Bangumi]):
        self.session.add_all(datas)
        self.session.commit()
        _invalidate_bangumi_cache()
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
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Update {data.official_title}")
        return True

    def update_all(self, datas: list[Bangumi]):
        self.session.add_all(datas)
        self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Update {len(datas)} bangumi.")

    def update_rss(self, title_raw: str, rss_set: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        result = self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.rss_link = rss_set
            bangumi.added = False
            self.session.add(bangumi)
            self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Update {title_raw} rss_link to {rss_set}.")

    def update_poster(self, title_raw: str, poster_link: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        result = self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.poster_link = poster_link
            self.session.add(bangumi)
            self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Update {title_raw} poster_link to {poster_link}.")

    def delete_one(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            self.session.delete(bangumi)
            self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Delete bangumi id: {_id}.")

    def delete_all(self):
        statement = delete(Bangumi)
        self.session.execute(statement)
        self.session.commit()
        _invalidate_bangumi_cache()

    def search_all(self) -> list[Bangumi]:
        global _bangumi_cache, _bangumi_cache_time
        now = time.time()
        if _bangumi_cache is not None and (now - _bangumi_cache_time) < _BANGUMI_CACHE_TTL:
            return _bangumi_cache
        statement = select(Bangumi)
        result = self.session.execute(statement)
        bangumis = list(result.scalars().all())
        # Expunge objects from session to prevent DetachedInstanceError when
        # cached objects are accessed from a different session/request context
        for b in bangumis:
            self.session.expunge(b)
        _bangumi_cache = bangumis
        _bangumi_cache_time = now
        return _bangumi_cache

    def search_id(self, _id: int) -> Optional[Bangumi]:
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi is None:
            logger.warning(f"[Database] Cannot find bangumi id: {_id}.")
            return None
        else:
            logger.debug(f"[Database] Find bangumi id: {_id}.")
            return bangumi

    def match_poster(self, bangumi_name: str) -> str:
        statement = select(Bangumi).where(
            func.instr(bangumi_name, Bangumi.official_title) > 0
        )
        result = self.session.execute(statement)
        data = result.scalar_one_or_none()
        if data:
            return data.poster_link
        else:
            return ""

    def match_list(self, torrent_list: list, rss_link: str) -> list:
        match_datas = self.search_all()
        if not match_datas:
            return torrent_list
        # Build index for faster lookup
        title_index = {m.title_raw: m for m in match_datas}
        unmatched = []
        rss_updated = set()
        for torrent in torrent_list:
            matched = False
            for title_raw, match_data in title_index.items():
                if title_raw in torrent.name:
                    if rss_link not in match_data.rss_link and title_raw not in rss_updated:
                        match_data.rss_link += f",{rss_link}"
                        match_data.added = False
                        rss_updated.add(title_raw)
                    matched = True
                    break
            if not matched:
                unmatched.append(torrent)
        # Batch commit all rss_link updates
        if rss_updated:
            self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Batch updated rss_link for {len(rss_updated)} bangumi.")
        return unmatched

    def match_torrent(self, torrent_name: str) -> Optional[Bangumi]:
        statement = (
            select(Bangumi)
            .where(
                and_(
                    func.instr(torrent_name, Bangumi.title_raw) > 0,
                    Bangumi.deleted == false(),
                )
            )
            # Prefer longer title_raw matches (more specific)
            .order_by(func.length(Bangumi.title_raw).desc())
            .limit(1)
        )
        result = self.session.execute(statement)
        return result.scalar_one_or_none()

    def not_complete(self) -> list[Bangumi]:
        condition = select(Bangumi).where(
            and_(Bangumi.eps_collect == false(), Bangumi.deleted == false())
        )
        result = self.session.execute(condition)
        return list(result.scalars().all())

    def not_added(self) -> list[Bangumi]:
        conditions = select(Bangumi).where(
            or_(
                Bangumi.added == 0,
                Bangumi.rule_name is None,
                Bangumi.save_path is None,
            )
        )
        result = self.session.execute(conditions)
        return list(result.scalars().all())

    def disable_rule(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.deleted = True
            self.session.add(bangumi)
            self.session.commit()
            logger.debug(f"[Database] Disable rule {bangumi.title_raw}.")

    def search_rss(self, rss_link: str) -> list[Bangumi]:
        statement = select(Bangumi).where(func.instr(rss_link, Bangumi.rss_link) > 0)
        result = self.session.execute(statement)
        return list(result.scalars().all())

    def archive_one(self, _id: int) -> bool:
        """Set archived=True for the given bangumi."""
        bangumi = self.session.get(Bangumi, _id)
        if not bangumi:
            logger.warning(f"[Database] Cannot archive bangumi id: {_id}, not found.")
            return False
        bangumi.archived = True
        self.session.add(bangumi)
        self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Archived bangumi id: {_id}.")
        return True

    def unarchive_one(self, _id: int) -> bool:
        """Set archived=False for the given bangumi."""
        bangumi = self.session.get(Bangumi, _id)
        if not bangumi:
            logger.warning(f"[Database] Cannot unarchive bangumi id: {_id}, not found.")
            return False
        bangumi.archived = False
        self.session.add(bangumi)
        self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Unarchived bangumi id: {_id}.")
        return True

    def match_by_save_path(self, save_path: str) -> Optional[Bangumi]:
        """Find bangumi by save_path to get offset."""
        statement = select(Bangumi).where(Bangumi.save_path == save_path)
        result = self.session.execute(statement)
        return result.scalar_one_or_none()

import logging
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from sqlmodel import and_, delete, false, or_, select

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
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, data: Bangumi) -> bool:
        statement = select(Bangumi).where(Bangumi.title_raw == data.title_raw)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            return False
        self.session.add(data)
        await self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Insert {data.official_title} into database.")
        return True

    async def add_all(self, datas: list[Bangumi]):
        self.session.add_all(datas)
        await self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Insert {len(datas)} bangumi into database.")

    async def update(self, data: Bangumi | BangumiUpdate, _id: int = None) -> bool:
        if _id and isinstance(data, BangumiUpdate):
            db_data = await self.session.get(Bangumi, _id)
        elif isinstance(data, Bangumi):
            db_data = await self.session.get(Bangumi, data.id)
        else:
            return False
        if not db_data:
            return False
        bangumi_data = data.dict(exclude_unset=True)
        for key, value in bangumi_data.items():
            setattr(db_data, key, value)
        self.session.add(db_data)
        await self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Update {data.official_title}")
        return True

    async def update_all(self, datas: list[Bangumi]):
        self.session.add_all(datas)
        await self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Update {len(datas)} bangumi.")

    async def update_rss(self, title_raw: str, rss_set: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.rss_link = rss_set
            bangumi.added = False
            self.session.add(bangumi)
            await self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Update {title_raw} rss_link to {rss_set}.")

    async def update_poster(self, title_raw: str, poster_link: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.poster_link = poster_link
            self.session.add(bangumi)
            await self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Update {title_raw} poster_link to {poster_link}.")

    async def delete_one(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            await self.session.delete(bangumi)
            await self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Delete bangumi id: {_id}.")

    async def delete_all(self):
        statement = delete(Bangumi)
        await self.session.execute(statement)
        await self.session.commit()
        _invalidate_bangumi_cache()

    async def search_all(self) -> list[Bangumi]:
        global _bangumi_cache, _bangumi_cache_time
        now = time.time()
        if _bangumi_cache is not None and (now - _bangumi_cache_time) < _BANGUMI_CACHE_TTL:
            return _bangumi_cache
        statement = select(Bangumi)
        result = await self.session.execute(statement)
        _bangumi_cache = list(result.scalars().all())
        _bangumi_cache_time = now
        return _bangumi_cache

    async def search_id(self, _id: int) -> Optional[Bangumi]:
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi is None:
            logger.warning(f"[Database] Cannot find bangumi id: {_id}.")
            return None
        else:
            logger.debug(f"[Database] Find bangumi id: {_id}.")
            return bangumi

    async def match_poster(self, bangumi_name: str) -> str:
        statement = select(Bangumi).where(
            func.instr(bangumi_name, Bangumi.official_title) > 0
        )
        result = await self.session.execute(statement)
        data = result.scalar_one_or_none()
        if data:
            return data.poster_link
        else:
            return ""

    async def match_list(self, torrent_list: list, rss_link: str) -> list:
        match_datas = await self.search_all()
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
            await self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(f"[Database] Batch updated rss_link for {len(rss_updated)} bangumi.")
        return unmatched

    async def match_torrent(self, torrent_name: str) -> Optional[Bangumi]:
        statement = select(Bangumi).where(
            and_(
                func.instr(torrent_name, Bangumi.title_raw) > 0,
                Bangumi.deleted == false(),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def not_complete(self) -> list[Bangumi]:
        condition = select(Bangumi).where(
            and_(Bangumi.eps_collect == false(), Bangumi.deleted == false())
        )
        result = await self.session.execute(condition)
        return list(result.scalars().all())

    async def not_added(self) -> list[Bangumi]:
        conditions = select(Bangumi).where(
            or_(
                Bangumi.added == 0,
                Bangumi.rule_name is None,
                Bangumi.save_path is None,
            )
        )
        result = await self.session.execute(conditions)
        return list(result.scalars().all())

    async def disable_rule(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.deleted = True
            self.session.add(bangumi)
            await self.session.commit()
            logger.debug(f"[Database] Disable rule {bangumi.title_raw}.")

    async def search_rss(self, rss_link: str) -> list[Bangumi]:
        statement = select(Bangumi).where(func.instr(rss_link, Bangumi.rss_link) > 0)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

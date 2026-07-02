"""aria2 gid 关联表数据库操作层。

只有 ``Aria2Downloader`` 会用到这张表：aria2 没有 tag/category，需要本地
持久化 gid -> bangumi_id / category / dedup_key 的映射。
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from module.models.aria2 import Aria2Gid

logger = logging.getLogger(__name__)


class Aria2GidDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        gid: str,
        bangumi_id: int | None = None,
        category: str | None = None,
        dedup_key: str | None = None,
    ) -> None:
        """新增一条 gid 记录，或者用非空字段覆盖已有记录。"""
        existing = await self.session.get(Aria2Gid, gid)
        if existing is None:
            self.session.add(
                Aria2Gid(
                    gid=gid,
                    bangumi_id=bangumi_id,
                    category=category,
                    dedup_key=dedup_key,
                )
            )
        else:
            if bangumi_id is not None:
                existing.bangumi_id = bangumi_id
            if category is not None:
                existing.category = category
            if dedup_key is not None:
                existing.dedup_key = dedup_key
            self.session.add(existing)
        await self.session.commit()

    async def get(self, gid: str) -> Aria2Gid | None:
        return await self.session.get(Aria2Gid, gid)

    async def get_many(self, gids: list[str]) -> dict[str, Aria2Gid]:
        if not gids:
            return {}
        result = await self.session.execute(
            select(Aria2Gid).where(Aria2Gid.gid.in_(gids))  # type: ignore[attr-defined]
        )
        return {row.gid: row for row in result.scalars().all()}

    async def find_by_dedup_key(self, dedup_key: str) -> str | None:
        """返回携带该 dedup_key 的已有 gid（没有则 None），用于新增前判重。"""
        result = await self.session.execute(
            select(Aria2Gid.gid).where(Aria2Gid.dedup_key == dedup_key)  # type: ignore[arg-type]
        )
        return result.scalars().first()

    async def set_category(self, gid: str, category: str) -> None:
        await self.upsert(gid, category=category)

    async def delete(self, gid: str) -> None:
        existing = await self.session.get(Aria2Gid, gid)
        if existing is not None:
            await self.session.delete(existing)
            await self.session.commit()

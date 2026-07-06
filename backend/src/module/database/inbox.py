"""通知中心消息表的仓储。合并/去重语义见 ``upsert``。"""

import logging
from typing import Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, func, select

from module.models.inbox import InboxMessage, utcnow_iso

logger = logging.getLogger(__name__)

DEFAULT_KEEP = 500


class InboxDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        *,
        kind: str,
        severity: str = "info",
        title: str = "",
        body: str = "",
        payload: Optional[str] = None,
        dedup_key: Optional[str] = None,
        once: bool = False,
        keep: int = DEFAULT_KEEP,
    ) -> Optional[InboxMessage]:
        """写入一条通知。

        - ``once=True``：同 ``dedup_key`` 的行（无论已读与否）存在则跳过，
          返回 None（如"新版本可用"每个版本只提醒一次）。
        - 否则若存在同 ``dedup_key`` 的**未读**行：合并——count+1、刷新
          updated_at、内容以最新为准（持续性故障不刷屏）。
        - 其余情况插入新行，并裁剪到最近 ``keep`` 条。
        """
        if dedup_key is not None:
            statement = select(InboxMessage).where(InboxMessage.dedup_key == dedup_key)
            if not once:
                statement = statement.where(InboxMessage.read == False)  # noqa: E712
            result = await self.session.execute(statement)
            existing = result.scalars().first()
            if existing is not None:
                if once:
                    return None
                existing.count += 1
                existing.severity = severity
                existing.title = title
                existing.body = body
                existing.payload = payload
                existing.updated_at = utcnow_iso()
                self.session.add(existing)
                await self.session.commit()
                return existing

        message = InboxMessage(
            kind=kind,
            severity=severity,
            title=title,
            body=body,
            payload=payload,
            dedup_key=dedup_key,
        )
        self.session.add(message)
        await self.session.commit()
        await self.prune(keep=keep)
        return message

    async def list(
        self, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> list[InboxMessage]:
        statement = select(InboxMessage)
        if unread_only:
            statement = statement.where(InboxMessage.read == False)  # noqa: E712
        statement = (
            statement.order_by(
                InboxMessage.updated_at.desc(),  # type: ignore[attr-defined]
                InboxMessage.id.desc(),  # type: ignore[attr-defined]
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_all(self, unread_only: bool = False) -> int:
        statement = select(func.count()).select_from(InboxMessage)
        if unread_only:
            statement = statement.where(InboxMessage.read == False)  # noqa: E712
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def unread_count(self) -> int:
        return await self.count_all(unread_only=True)

    async def latest_id(self) -> int:
        result = await self.session.execute(
            select(func.max(InboxMessage.id)).select_from(InboxMessage)
        )
        return int(result.scalar_one() or 0)

    async def mark_read(self, message_id: int) -> bool:
        message = await self.session.get(InboxMessage, message_id)
        if message is None:
            return False
        message.read = True
        self.session.add(message)
        await self.session.commit()
        return True

    async def mark_all_read(self) -> int:
        result = await self.session.execute(
            update(InboxMessage)
            .where(InboxMessage.read == False)  # type: ignore[arg-type]  # noqa: E712
            .values(read=True)
        )
        await self.session.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def delete(self, message_id: int) -> bool:
        message = await self.session.get(InboxMessage, message_id)
        if message is None:
            return False
        await self.session.delete(message)
        await self.session.commit()
        return True

    async def clear(self) -> int:
        result = await self.session.execute(delete(InboxMessage))
        await self.session.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def prune(self, keep: int = DEFAULT_KEEP) -> int:
        """删除最近 ``keep`` 条以外的旧消息，返回删除数量。"""
        stale_ids_stmt = (
            select(InboxMessage.id)
            .order_by(
                InboxMessage.updated_at.desc(),  # type: ignore[attr-defined]
                InboxMessage.id.desc(),  # type: ignore[attr-defined]
            )
            .offset(keep)
        )
        result = await self.session.execute(stale_ids_stmt)
        stale_ids = list(result.scalars().all())
        if not stale_ids:
            return 0
        await self.session.execute(
            delete(InboxMessage).where(InboxMessage.id.in_(stale_ids))  # type: ignore[attr-defined]
        )
        await self.session.commit()
        return len(stale_ids)

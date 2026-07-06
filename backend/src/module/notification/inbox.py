"""站内通知中心的持久化 sink。

``record_event`` 把 SystemEvent 落库（``async with Database()``，
session-per-operation）；``inbox_revision`` 是进程内单调递增的修订号，
任何入库/已读/删除操作都会 bump，SSE 循环据此决定是否需要查库推送，
避免每个 tick 都打一次数据库。AB 为单进程部署，进程内计数即可。
"""

import json
import logging

from module.database import Database
from module.notification.events import SystemEvent

logger = logging.getLogger(__name__)

INBOX_KEEP = 500

_revision: int = 1


def inbox_revision() -> int:
    return _revision


def bump_inbox_revision() -> None:
    global _revision
    _revision += 1


async def record_event(event: SystemEvent) -> int:
    """事件入库，返回消息 id；被 once 去重跳过时返回 0。"""
    title, body = event.describe()
    async with Database() as db:
        message = await db.inbox.upsert(
            kind=event.kind,
            severity=event.severity,
            title=title,
            body=body,
            payload=json.dumps(event.payload(), ensure_ascii=False),
            dedup_key=event.dedup_key(),
            once=event.once,
            keep=INBOX_KEEP,
        )
    if message is None:
        return 0
    bump_inbox_revision()
    return message.id

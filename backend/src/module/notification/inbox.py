"""站内通知中心的持久化 sink。

``record_event`` 把 SystemEvent 落库（``async with Database()``，
session-per-operation）；``inbox_revision`` 是进程内单调递增的修订号，
任何入库/已读/删除操作都会 bump，并在事件总线上发布 :class:`InboxChanged`。
SSE 连接订阅该事件，收到后才查库推送未读数（取代原先每 3s 比较修订号的轮询）。
AB 为单进程部署，进程内计数即可。
"""

import json
import logging
from dataclasses import dataclass
from typing import ClassVar

from ab_sdk import Event
from module.database import Database
from module.notification.events import SystemEvent
from module.plugin.host import publish

logger = logging.getLogger(__name__)

INBOX_KEEP = 500

_revision: int = 1


@dataclass(frozen=True, slots=True)
class InboxChanged(Event):
    """站内通知中心有变化（新消息、已读、删除），``revision`` 为新的修订号。"""

    kind: ClassVar[str] = "inbox.changed"
    revision: int


def inbox_revision() -> int:
    return _revision


def bump_inbox_revision() -> None:
    global _revision
    _revision += 1
    publish(InboxChanged(revision=_revision))


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

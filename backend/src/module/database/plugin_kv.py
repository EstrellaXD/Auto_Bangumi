"""插件键值仓储：值以 JSON 文本存储。"""

import json
from typing import Any

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from module.models.plugin_kv import PluginKV, _utcnow


class PluginKVDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, plugin_id: str, key: str) -> tuple[bool, Any]:
        """返回 (是否存在, 值)，以区分「不存在」与「存的就是 null」。"""
        result = await self.session.execute(
            select(PluginKV.value).where(
                PluginKV.plugin_id == plugin_id, PluginKV.key == key
            )
        )
        raw = result.scalars().first()
        if raw is None:
            return False, None
        return True, json.loads(raw)

    async def set(self, plugin_id: str, key: str, value: Any) -> None:
        raw = json.dumps(value, ensure_ascii=False)
        now = _utcnow()
        await self.session.execute(
            sqlite_insert(PluginKV)
            .values(plugin_id=plugin_id, key=key, value=raw, updated_at=now)
            .on_conflict_do_update(
                index_elements=["plugin_id", "key"],
                set_={"value": raw, "updated_at": now},
            )
        )
        await self.session.commit()

    async def delete(self, plugin_id: str, key: str) -> None:
        await self.session.execute(
            delete(PluginKV).where(
                PluginKV.plugin_id == plugin_id,  # type: ignore[arg-type]
                PluginKV.key == key,  # type: ignore[arg-type]
            )
        )
        await self.session.commit()

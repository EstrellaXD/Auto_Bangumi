"""aria2 gid 关联表数据库操作层。

只有 ``Aria2Downloader`` 会用到这张表：aria2 没有 tag/category，需要本地
持久化 gid -> bangumi_id / category / dedup_key 的映射。
"""

import json
import logging
from dataclasses import asdict, dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from module.models.aria2 import Aria2Gid

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Aria2RenameIntent:
    """Durable proof that this gid owned a filesystem move before it started."""

    old_path: str
    new_path: str
    st_dev: int
    st_ino: int
    st_size: int
    st_mtime_ns: int

    def to_json(self) -> str:
        return json.dumps(
            {"version": 1, **asdict(self)}, ensure_ascii=False, sort_keys=True
        )

    @classmethod
    def from_json(cls, raw: str | None) -> "Aria2RenameIntent | None":
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict) or data.get("version") != 1:
            return None
        path_fields = ("old_path", "new_path")
        stat_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if any(not isinstance(data.get(field), str) for field in path_fields):
            return None
        if any(type(data.get(field)) is not int for field in stat_fields):
            return None
        return cls(**{field: data[field] for field in (*path_fields, *stat_fields)})


class Aria2GidDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        gid: str,
        bangumi_id: int | None = None,
        category: str | None = None,
        dedup_key: str | None = None,
        renamed_paths: str | None = None,
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
                    renamed_paths=renamed_paths,
                )
            )
        else:
            if bangumi_id is not None:
                existing.bangumi_id = bangumi_id
            if category is not None:
                existing.category = category
            if dedup_key is not None:
                existing.dedup_key = dedup_key
            if renamed_paths is not None:
                existing.renamed_paths = renamed_paths
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

    async def replace_gid(self, old_gid: str, new_gid: str) -> None:
        """Move local metadata from an aria2 metadata gid to its followedBy gid."""
        if old_gid == new_gid:
            return
        old = await self.session.get(Aria2Gid, old_gid)
        if old is None:
            return
        existing = await self.session.get(Aria2Gid, new_gid)
        if existing is None:
            self.session.add(
                Aria2Gid(
                    gid=new_gid,
                    bangumi_id=old.bangumi_id,
                    category=old.category,
                    dedup_key=old.dedup_key,
                    renamed_paths=old.renamed_paths,
                    rename_intent=old.rename_intent,
                    created_at=old.created_at,
                )
            )
        else:
            if existing.bangumi_id is None:
                existing.bangumi_id = old.bangumi_id
            if existing.category is None:
                existing.category = old.category
            if existing.dedup_key is None:
                existing.dedup_key = old.dedup_key
            existing.renamed_paths = _merge_renamed_paths(
                existing.renamed_paths, old.renamed_paths
            )
            if existing.rename_intent is None:
                existing.rename_intent = old.rename_intent
            self.session.add(existing)
        await self.session.delete(old)
        await self.session.commit()

    async def get_renamed_paths(self, gid: str) -> dict[str, str]:
        record = await self.session.get(Aria2Gid, gid)
        if record is None or not record.renamed_paths:
            return {}
        try:
            data = json.loads(record.renamed_paths)
        except json.JSONDecodeError:
            logger.warning("Ignoring invalid renamed_paths for gid %s", gid)
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    async def set_renamed_path(self, gid: str, old_path: str, new_path: str) -> None:
        mapping = await self.get_renamed_paths(gid)
        for original_path, renamed_path in list(mapping.items()):
            if renamed_path == old_path:
                mapping[original_path] = new_path
        mapping[old_path] = new_path
        await self.upsert(gid, renamed_paths=json.dumps(mapping, ensure_ascii=False))

    async def get_rename_intent(self, gid: str) -> Aria2RenameIntent | None:
        record = await self.session.get(Aria2Gid, gid)
        if record is None or not record.rename_intent:
            return None
        intent = Aria2RenameIntent.from_json(record.rename_intent)
        if intent is None:
            logger.warning("Ignoring invalid rename_intent for gid %s", gid)
        return intent

    async def set_rename_intent(self, gid: str, intent: Aria2RenameIntent) -> None:
        record = await self.session.get(Aria2Gid, gid)
        if record is None:
            record = Aria2Gid(gid=gid)
        record.rename_intent = intent.to_json()
        self.session.add(record)
        await self.session.commit()

    async def clear_rename_intent(
        self,
        gid: str,
        expected: Aria2RenameIntent | None = None,
    ) -> bool:
        record = await self.session.get(Aria2Gid, gid)
        if record is None:
            return False
        if (
            expected is not None
            and Aria2RenameIntent.from_json(record.rename_intent) != expected
        ):
            return False
        record.rename_intent = None
        self.session.add(record)
        await self.session.commit()
        return True

    async def finalize_rename_intent(
        self, gid: str, expected: Aria2RenameIntent
    ) -> bool:
        """Commit the sidecar mapping and clear its matching intent together."""
        record = await self.session.get(Aria2Gid, gid)
        if (
            record is None
            or Aria2RenameIntent.from_json(record.rename_intent) != expected
        ):
            return False
        mapping = _decode_renamed_paths(record.renamed_paths)
        for original_path, renamed_path in list(mapping.items()):
            if renamed_path == expected.old_path:
                mapping[original_path] = expected.new_path
        mapping[expected.old_path] = expected.new_path
        record.renamed_paths = json.dumps(mapping, ensure_ascii=False)
        record.rename_intent = None
        self.session.add(record)
        await self.session.commit()
        return True

    async def delete(self, gid: str) -> None:
        existing = await self.session.get(Aria2Gid, gid)
        if existing is not None:
            await self.session.delete(existing)
            await self.session.commit()


def _merge_renamed_paths(left: str | None, right: str | None) -> str | None:
    if not left:
        return right
    if not right:
        return left
    try:
        merged = json.loads(left)
        incoming = json.loads(right)
    except json.JSONDecodeError:
        return left
    if not isinstance(merged, dict) or not isinstance(incoming, dict):
        return left
    merged.update(incoming)
    return json.dumps(merged, ensure_ascii=False)


def _decode_renamed_paths(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}

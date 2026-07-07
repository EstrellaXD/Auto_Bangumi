import json
import logging
import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from sqlmodel import and_, delete, false, or_, select

from module.models import Bangumi, BangumiUpdate

logger = logging.getLogger(__name__)


def _normalize_group_name(group: str | None) -> str:
    """Normalize group name for comparison by removing common separators."""
    if not group:
        return ""
    # Remove common separators (&, ×, _, -) and normalize to lowercase
    return re.sub(r"[&×_\-]", "", group).lower().strip()


def _groups_are_similar(group1: str | None, group2: str | None) -> bool:
    """
    Check if two group names are similar enough to be considered the same group.

    Handles cases like:
    - "LoliHouse" vs "LoliHouse&动漫国字幕组"
    - "字幕组A" vs "字幕组A×字幕组B"
    """
    if not group1 or not group2:
        return False

    # Exact match or substring match (one contains the other)
    if group1 == group2 or group1 in group2 or group2 in group1:
        return True

    # Normalized comparison - check if core group names overlap
    norm1 = _normalize_group_name(group1)
    norm2 = _normalize_group_name(group2)
    return norm1 in norm2 or norm2 in norm1


def _get_aliases_list(bangumi: Bangumi) -> list[str]:
    """Get the list of title aliases from a bangumi's title_aliases JSON field."""
    if not bangumi.title_aliases:
        return []
    try:
        aliases = json.loads(bangumi.title_aliases)
        if not isinstance(aliases, list):
            return []
        return [a for a in aliases if a]
    except (json.JSONDecodeError, TypeError):
        return []


def _set_aliases_list(bangumi: Bangumi, aliases: list[str]) -> None:
    """Set the title aliases JSON field from a list."""
    if not aliases:
        bangumi.title_aliases = None
    else:
        # Remove duplicates while preserving order
        unique_aliases = list(dict.fromkeys(aliases))
        bangumi.title_aliases = json.dumps(unique_aliases, ensure_ascii=False)


def _all_title_patterns(bangumi: Bangumi) -> list[str]:
    """All title patterns for matching (title_raw + all aliases)."""
    patterns = []
    if bangumi.title_raw:
        patterns.append(bangumi.title_raw)
    patterns.extend(_get_aliases_list(bangumi))
    return patterns


def normalize_save_path(save_path: str | None) -> str:
    """Normalize a save_path so equivalent paths compare equal.

    Collapses the separator/trailing-slash variations that
    `BangumiDatabase.match_by_save_path` used to try one at a time.
    """
    if not save_path:
        return ""
    return save_path.replace("\\", "/").rstrip("/")


def build_save_path_index(bangumi_list: list[Bangumi]) -> dict[str, Bangumi]:
    """Build an in-memory normalized-save_path -> Bangumi index.

    Lets callers match many torrents against an already-loaded bangumi list
    (O(1) per lookup) instead of issuing a DB query per torrent.
    """
    index: dict[str, Bangumi] = {}
    for bangumi in bangumi_list:
        if bangumi.deleted or not bangumi.save_path:
            continue
        key = normalize_save_path(bangumi.save_path)
        if key:
            index.setdefault(key, bangumi)
    return index


def _find_semantic_match(data: Bangumi, candidates: list[Bangumi]) -> Optional[Bangumi]:
    """在已加载的候选列表中查找语义重复项（同一部番剧、命名规则不同）。

    被 ``find_semantic_duplicate``（单条、逐条查库）和 ``add_all``（批量、
    候选一次性查库后在内存中匹配）共用，匹配规则只维护一处。
    """
    for candidate in candidates:
        is_exact_duplicate = (
            candidate.title_raw == data.title_raw
            and candidate.group_name == data.group_name
        )
        if is_exact_duplicate:
            continue

        is_semantic_match = (
            candidate.dpi == data.dpi
            and candidate.subtitle == data.subtitle
            and candidate.source == data.source
            and _groups_are_similar(candidate.group_name, data.group_name)
        )
        if is_semantic_match:
            return candidate

    return None


def _inherit_year(data: Bangumi, candidates: list[Bangumi]) -> None:
    """新条目缺年份时继承同名已有条目的年份。

    save path 由 ``official_title (year)`` 组成（downloader/path.py），同一部
    番剧的不同订阅条目（不同字幕组/清晰度）若年份不一致，会被拆进两个媒体库
    目录。Mikan 解析路径不填 year，因此从已有同名条目补齐。
    """
    if data.year:
        return
    for candidate in candidates:
        if candidate.year:
            data.year = candidate.year
            return


def match_bangumi_in_list(
    torrent_name: str, bangumi_list: list[Bangumi]
) -> Optional[Bangumi]:
    """Match a torrent name against an already-loaded list of bangumi.

    Pure/in-memory: the RSS refresh cycle loads the active bangumi once and
    matches every torrent against it here, instead of querying per torrent
    (the job the old module-level TTL cache used to do). Returns the bangumi
    with the longest matching pattern for specificity.
    """
    best_match: Optional[Bangumi] = None
    best_match_len = 0
    for bangumi in bangumi_list:
        if bangumi.deleted:
            continue
        for pattern in _all_title_patterns(bangumi):
            if pattern in torrent_name and len(pattern) > best_match_len:
                best_match = bangumi
                best_match_len = len(pattern)
    return best_match


class BangumiDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _same_title_candidates(self, official_title: str) -> list[Bangumi]:
        """加载与给定 official_title 同名的所有未删除条目。"""
        statement = select(Bangumi).where(
            and_(
                Bangumi.official_title == official_title,
                Bangumi.deleted == false(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def find_semantic_duplicate(self, data: Bangumi) -> Optional[Bangumi]:
        """
        Find existing bangumi that semantically matches the new one.

        This handles cases where subtitle groups change naming mid-season.
        A semantic match requires:
        - Same official_title
        - Same dpi (resolution)
        - Same subtitle type
        - Same source
        - Similar group_name (one contains the other)

        Returns the matching Bangumi if found, None otherwise.
        """
        candidates = await self._same_title_candidates(data.official_title)
        match = _find_semantic_match(data, candidates)
        if match:
            logger.debug(
                "Found semantic duplicate: '%s' matches "
                "existing '%s' (official: %s)",
                data.title_raw,
                match.title_raw,
                data.official_title,
            )
        return match

    async def add_title_alias(
        self, bangumi_id: int, new_title_raw: str | None, auto_commit: bool = True
    ) -> bool:
        """
        Add a new title_raw alias to an existing bangumi.

        This allows a single bangumi entry to match multiple naming patterns.
        """
        bangumi = await self.session.get(Bangumi, bangumi_id)
        if not bangumi:
            logger.warning(f"Cannot add alias: bangumi id {bangumi_id} not found")
            return False

        # Don't add None or empty aliases
        if not new_title_raw:
            return False

        # Don't add if it's the same as the main title_raw
        if bangumi.title_raw == new_title_raw:
            return False

        # Get existing aliases and add the new one
        aliases = _get_aliases_list(bangumi)
        if new_title_raw in aliases:
            return False  # Already exists

        aliases.append(new_title_raw)
        _set_aliases_list(bangumi, aliases)

        self.session.add(bangumi)
        if auto_commit:
            await self.session.commit()
        logger.info(
            f"Added alias '{new_title_raw}' to bangumi '{bangumi.official_title}' "
            f"(id: {bangumi_id})"
        )
        return True

    def get_all_title_patterns(self, bangumi: Bangumi) -> list[str]:
        """Get all title patterns for matching (title_raw + all aliases)."""
        return _all_title_patterns(bangumi)

    async def find_duplicate(self, data: Bangumi) -> Optional[Bangumi]:
        """Find an existing bangumi with the same title_raw and group_name.

        Legacy data may contain multiple rows for the same key; return the
        oldest (lowest id) deterministically and warn instead of raising.
        """
        statement = (
            select(Bangumi)
            .where(
                and_(
                    Bangumi.title_raw == data.title_raw,
                    Bangumi.group_name == data.group_name,
                )
            )
            .order_by(Bangumi.id)  # type: ignore[arg-type]
        )
        result = await self.session.execute(statement)
        rows = list(result.scalars().all())
        if len(rows) > 1:
            logger.warning(
                "Multiple bangumi rows share (title_raw=%s, group_name=%s); "
                "using the oldest (id=%s)",
                data.title_raw,
                data.group_name,
                rows[0].id,
            )
        return rows[0] if rows else None

    async def _is_duplicate(self, data: Bangumi) -> bool:
        """Check if a bangumi rule already exists based on title_raw and group_name."""
        return await self.find_duplicate(data) is not None

    async def add(self, data: Bangumi) -> bool:
        if await self._is_duplicate(data):
            logger.debug(
                "Skipping duplicate: %s (%s)",
                data.official_title,
                data.group_name,
            )
            return False

        # Check for semantic duplicate (same anime, different naming pattern)
        candidates = await self._same_title_candidates(data.official_title)
        semantic_match = _find_semantic_match(data, candidates)
        if semantic_match:
            # Add as alias instead of creating new entry
            await self.add_title_alias(semantic_match.id, data.title_raw)
            logger.info(
                f"Merged '{data.title_raw}' as alias to existing "
                f"'{semantic_match.title_raw}' (official: {data.official_title})"
            )
            return False  # Return False since we didn't add a new entry

        _inherit_year(data, candidates)
        self.session.add(data)
        await self.session.commit()
        logger.debug("Insert %s into database.", data.official_title)
        return True

    async def add_all(self, datas: list[Bangumi]) -> int:
        """Add multiple bangumi, skipping duplicates. Returns count of added items."""
        if not datas:
            return 0

        # Batch query: get all existing (title_raw, group_name) combinations in one query
        # This replaces N individual _is_duplicate() calls with a single SELECT
        keys_to_check = [(d.title_raw, d.group_name) for d in datas]
        conditions = [
            and_(Bangumi.title_raw == tr, Bangumi.group_name == gn)
            for tr, gn in keys_to_check
        ]
        if conditions:
            statement = select(Bangumi.title_raw, Bangumi.group_name).where(
                or_(*conditions)
            )
            result = await self.session.execute(statement)
            existing = set(result.all())
        else:
            existing = set()

        # Filter out exact duplicates
        to_add = [d for d in datas if (d.title_raw, d.group_name) not in existing]

        # Batch query: load all semantic-duplicate candidates (grouped by
        # official_title) in one SELECT, instead of one find_semantic_duplicate()
        # query per candidate. Safe because no rows are inserted mid-loop —
        # add_title_alias() only mutates existing rows and the new bangumi are
        # only added to the session after this loop finishes.
        official_titles = {d.official_title for d in to_add}
        candidates_by_title: dict[str, list[Bangumi]] = {}
        if official_titles:
            # SQLModel 类属性在 mypy 看来是普通字段类型而非 InstrumentedAttribute，
            # 无法识别 .in_() 等查询方法（无官方 mypy 插件支持）。
            dup_statement = select(Bangumi).where(
                and_(
                    Bangumi.official_title.in_(official_titles),  # type: ignore[attr-defined]
                    Bangumi.deleted == false(),
                )
            )
            result = await self.session.execute(dup_statement)
            for candidate in result.scalars().all():
                candidates_by_title.setdefault(candidate.official_title, []).append(
                    candidate
                )

        # Check for semantic duplicates and add as aliases
        semantic_merged = 0
        really_to_add = []
        for d in to_add:
            semantic_match = _find_semantic_match(
                d, candidates_by_title.get(d.official_title, [])
            )
            if semantic_match:
                # Add as alias instead of creating new entry (defer commit)
                await self.add_title_alias(
                    semantic_match.id, d.title_raw, auto_commit=False
                )
                semantic_merged += 1
                logger.info(
                    f"Merged '{d.title_raw}' as alias to existing "
                    f"'{semantic_match.title_raw}' (official: {d.official_title})"
                )
            else:
                _inherit_year(d, candidates_by_title.get(d.official_title, []))
                really_to_add.append(d)

        # Also deduplicate within the batch itself
        seen = set()
        unique_to_add = []
        for d in really_to_add:
            key = (d.title_raw, d.group_name)
            if key not in seen:
                seen.add(key)
                unique_to_add.append(d)

        if not unique_to_add:
            if semantic_merged > 0:
                await self.session.commit()
                logger.debug(
                    "%s bangumi merged as aliases, " "rest were duplicates.",
                    semantic_merged,
                )
            else:
                logger.debug(
                    "All %s bangumi already exist, skipping.",
                    len(datas),
                )
            return 0

        self.session.add_all(unique_to_add)
        await self.session.commit()
        skipped = len(datas) - len(unique_to_add) - semantic_merged
        if skipped > 0 or semantic_merged > 0:
            logger.debug(
                "Insert %s bangumi, " "skipped %s duplicates, merged %s as aliases.",
                len(unique_to_add),
                skipped,
                semantic_merged,
            )
        else:
            logger.debug(
                "Insert %s bangumi into database.",
                len(unique_to_add),
            )
        return len(unique_to_add)

    async def update(
        self, data: Bangumi | BangumiUpdate, _id: int | None = None
    ) -> bool:
        if _id and isinstance(data, BangumiUpdate):
            db_data = await self.session.get(Bangumi, _id)
        elif isinstance(data, Bangumi):
            db_data = await self.session.get(Bangumi, data.id)
        else:
            return False
        if not db_data:
            return False
        bangumi_data = data.model_dump(exclude_unset=True)
        for key, value in bangumi_data.items():
            setattr(db_data, key, value)
        self.session.add(db_data)
        await self.session.commit()
        logger.debug("Update %s", data.official_title)
        return True

    async def update_all(self, datas: list[Bangumi]):
        self.session.add_all(datas)
        await self.session.commit()
        logger.debug("Update %s bangumi.", len(datas))

    async def update_rss(self, title_raw: str, rss_set: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.rss_link = rss_set
            bangumi.added = False
            self.session.add(bangumi)
            await self.session.commit()
            logger.debug("Update %s rss_link to %s.", title_raw, rss_set)

    async def update_poster(self, title_raw: str, poster_link: str):
        statement = select(Bangumi).where(Bangumi.title_raw == title_raw)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            bangumi.poster_link = poster_link
            self.session.add(bangumi)
            await self.session.commit()
            logger.debug("Update %s poster_link to %s.", title_raw, poster_link)

    async def mark_eps_collect(self, _id: int) -> None:
        """只把 eps_collect 置位，不触碰行内其他字段（offset/filter 等）。"""
        bangumi = await self.session.get(Bangumi, _id)
        if bangumi:
            bangumi.eps_collect = True
            self.session.add(bangumi)
            await self.session.commit()

    async def delete_one(self, _id: int):
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi:
            await self.session.delete(bangumi)
            await self.session.commit()
            logger.debug("Delete bangumi id: %s.", _id)

    async def delete_all(self):
        statement = delete(Bangumi)
        await self.session.execute(statement)
        await self.session.commit()

    async def search_all(self) -> list[Bangumi]:
        statement = select(Bangumi)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def search_id(self, _id: int) -> Optional[Bangumi]:
        statement = select(Bangumi).where(Bangumi.id == _id)
        result = await self.session.execute(statement)
        bangumi = result.scalar_one_or_none()
        if bangumi is None:
            logger.warning(f"Cannot find bangumi id: {_id}.")
            return None
        logger.debug("Find bangumi id: %s.", _id)
        return bangumi

    async def search_official_title(self, official_title: str) -> Optional[Bangumi]:
        statement = select(Bangumi).where(Bangumi.official_title == official_title)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def search_ids(self, ids: list[int]) -> list[Bangumi]:
        """Batch lookup multiple bangumi by their IDs."""
        if not ids:
            return []
        statement = select(Bangumi).where(Bangumi.id.in_(ids))  # type: ignore[attr-defined]
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def match_poster(self, bangumi_name: str) -> str:
        statement = select(Bangumi).where(
            func.instr(bangumi_name, Bangumi.official_title) > 0
        )
        result = await self.session.execute(statement)
        data = result.scalar_one_or_none()
        return (data.poster_link or "") if data else ""

    async def match_list(self, torrent_list: list, rss_link: str) -> list:
        match_datas = await self.search_all()
        if not match_datas:
            return torrent_list

        # Build index for O(1) lookup after regex match
        # Include both title_raw and all aliases
        title_index: dict[str, Bangumi] = {}
        for m in match_datas:
            # Add main title_raw (skip if None to avoid TypeError in sorted())
            if m.title_raw:
                title_index[m.title_raw] = m
            # Add all aliases
            for alias in _get_aliases_list(m):
                if alias:
                    title_index[alias] = m

        # Build compiled regex pattern for fast substring matching
        # Sort by length descending so longer (more specific) matches are found first
        sorted_titles = sorted(title_index.keys(), key=len, reverse=True)
        # Escape special regex characters and join with alternation
        pattern = "|".join(re.escape(title) for title in sorted_titles)
        title_regex = re.compile(pattern)

        unmatched = []
        rss_updated = set()
        for torrent in torrent_list:
            match = title_regex.search(torrent.name)
            if match:
                matched_title = match.group(0)
                match_data = title_index[matched_title]
                # Use the bangumi's main title_raw for rss_updated tracking
                if (
                    rss_link not in match_data.rss_link
                    and match_data.title_raw not in rss_updated
                ):
                    match_data = await self.session.merge(match_data)
                    match_data.rss_link += f",{rss_link}"
                    match_data.added = False
                    rss_updated.add(match_data.title_raw)
            else:
                unmatched.append(torrent)
        # Batch commit all rss_link updates
        if rss_updated:
            await self.session.commit()
            logger.debug(
                "Batch updated rss_link for %s bangumi.",
                len(rss_updated),
            )
        return unmatched

    async def match_torrent(self, torrent_name: str) -> Optional[Bangumi]:
        """
        Match torrent name to a bangumi, checking both title_raw and title_aliases.

        Returns the bangumi with the longest matching pattern for specificity.
        """
        match_datas = await self.search_all()
        return match_bangumi_in_list(torrent_name, match_datas)

    async def not_complete(self) -> list[Bangumi]:
        condition = select(Bangumi).where(
            and_(Bangumi.eps_collect == false(), Bangumi.deleted == false())
        )
        result = await self.session.execute(condition)
        return list(result.scalars().all())

    async def not_added(self) -> list[Bangumi]:
        # SQLModel 类属性在 mypy 看来是普通字段类型而非 InstrumentedAttribute，
        # 无法识别 .is_() 等查询方法（无官方 mypy 插件支持）。
        conditions = select(Bangumi).where(
            or_(
                Bangumi.added == 0,
                Bangumi.rule_name.is_(None),  # type: ignore[union-attr]
                Bangumi.save_path.is_(None),  # type: ignore[union-attr]
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
            logger.debug("Disable rule %s.", bangumi.title_raw)

    async def search_rss(self, rss_link: str) -> list[Bangumi]:
        statement = select(Bangumi).where(func.instr(rss_link, Bangumi.rss_link) > 0)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def archive_one(self, _id: int) -> bool:
        """Set archived=True for the given bangumi."""
        bangumi = await self.session.get(Bangumi, _id)
        if not bangumi:
            logger.warning(f"Cannot archive bangumi id: {_id}, not found.")
            return False
        bangumi.archived = True
        self.session.add(bangumi)
        await self.session.commit()
        logger.debug("Archived bangumi id: %s.", _id)
        return True

    async def unarchive_one(self, _id: int) -> bool:
        """Set archived=False for the given bangumi."""
        bangumi = await self.session.get(Bangumi, _id)
        if not bangumi:
            logger.warning(f"Cannot unarchive bangumi id: {_id}, not found.")
            return False
        bangumi.archived = False
        self.session.add(bangumi)
        await self.session.commit()
        logger.debug("Unarchived bangumi id: %s.", _id)
        return True

    async def match_by_save_path(self, save_path: str) -> Optional[Bangumi]:
        """Find bangumi by save_path to get offset.

        Tries exact match first, then falls back to matching with/without trailing slashes
        and different path separators.

        Note: When multiple subscriptions share the same save_path (e.g., different RSS
        sources for the same anime), this returns the first match. Use match_torrent()
        for more accurate matching when torrent_name is available.
        """
        if not save_path:
            return None

        # Try exact match first
        statement = select(Bangumi).where(
            and_(Bangumi.save_path == save_path, Bangumi.deleted == false())
        )
        result = await self.session.execute(statement)
        bangumi = result.scalars().first()
        if bangumi:
            return bangumi

        # Normalize the input path and try variations
        normalized = save_path.replace("\\", "/").rstrip("/")
        variations = [
            normalized,
            normalized + "/",
            save_path.rstrip("/"),
            save_path.rstrip("\\"),
        ]
        # Remove duplicates while preserving order
        seen = {save_path}
        unique_variations = []
        for v in variations:
            if v not in seen:
                seen.add(v)
                unique_variations.append(v)

        for variant in unique_variations:
            statement = select(Bangumi).where(
                and_(Bangumi.save_path == variant, Bangumi.deleted == false())
            )
            result = await self.session.execute(statement)
            bangumi = result.scalars().first()
            if bangumi:
                return bangumi

        return None

    async def get_needs_review(self) -> list[Bangumi]:
        """Get all bangumi that need review for offset mismatch."""
        statement = select(Bangumi).where(
            and_(
                Bangumi.needs_review == True,  # noqa: E712
                Bangumi.deleted == false(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_for_scan(self) -> list[Bangumi]:
        """Get all active (non-deleted, non-archived) bangumi for offset scanning."""
        statement = select(Bangumi).where(
            and_(
                Bangumi.deleted == false(),
                Bangumi.archived == false(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def set_needs_review(
        self,
        _id: int,
        reason: str,
        suggested_season_offset: int | None = None,
        suggested_episode_offset: int | None = None,
    ) -> bool:
        """Mark a bangumi as needing review with suggested offsets.

        Args:
            _id: The bangumi ID
            reason: Human-readable reason for the review
            suggested_season_offset: Suggested season offset value
            suggested_episode_offset: Suggested episode offset value
        """
        bangumi = await self.session.get(Bangumi, _id)
        if not bangumi:
            return False
        bangumi.needs_review = True
        bangumi.needs_review_reason = reason
        bangumi.suggested_season_offset = suggested_season_offset
        bangumi.suggested_episode_offset = suggested_episode_offset
        self.session.add(bangumi)
        await self.session.commit()
        logger.debug(
            "Marked bangumi id %s as needs_review: %s "
            "(suggested: season=%s, episode=%s)",
            _id,
            reason,
            suggested_season_offset,
            suggested_episode_offset,
        )
        return True

    async def apply_offset(self, _id: int) -> bool:
        """将建议的季度/集数偏移写入正式的 season_offset/episode_offset，并清除检查标记。

        Args:
            _id: The bangumi ID
        """
        bangumi = await self.session.get(Bangumi, _id)
        if not bangumi:
            return False
        if bangumi.suggested_season_offset is not None:
            bangumi.season_offset = bangumi.suggested_season_offset
        if bangumi.suggested_episode_offset is not None:
            bangumi.episode_offset = bangumi.suggested_episode_offset
        bangumi.needs_review = False
        bangumi.needs_review_reason = None
        bangumi.suggested_season_offset = None
        bangumi.suggested_episode_offset = None
        self.session.add(bangumi)
        await self.session.commit()
        logger.debug(
            "Applied offset for bangumi id %s: season=%s, episode=%s",
            _id,
            bangumi.season_offset,
            bangumi.episode_offset,
        )
        return True

    async def clear_needs_review(self, _id: int) -> bool:
        """Clear the needs_review flag and suggested offsets for a bangumi."""
        bangumi = await self.session.get(Bangumi, _id)
        if not bangumi:
            return False
        bangumi.needs_review = False
        bangumi.needs_review_reason = None
        bangumi.suggested_season_offset = None
        bangumi.suggested_episode_offset = None
        self.session.add(bangumi)
        await self.session.commit()
        logger.debug("Cleared needs_review for bangumi id %s", _id)
        return True

    async def set_weekday(self, _id: int, weekday: int | None) -> bool:
        """Set air_weekday and weekday_locked for manual calendar assignment."""
        bangumi = await self.session.get(Bangumi, _id)
        if not bangumi:
            return False
        if weekday is not None:
            bangumi.air_weekday = weekday
            bangumi.weekday_locked = True
        else:
            bangumi.air_weekday = None
            bangumi.weekday_locked = False
        self.session.add(bangumi)
        await self.session.commit()
        logger.debug(
            "Set weekday=%s, locked=%s for bangumi id %s",
            weekday,
            bangumi.weekday_locked,
            _id,
        )
        return True

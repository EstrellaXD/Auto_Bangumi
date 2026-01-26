import logging
import re
import time
from typing import Optional

from sqlalchemy.sql import func
from sqlmodel import Session, and_, delete, false, or_, select

from module.models import Bangumi, BangumiUpdate

logger = logging.getLogger(__name__)

# Module-level TTL cache for search_all results
_bangumi_cache: list[Bangumi] | None = None
_bangumi_cache_time: float = 0
_BANGUMI_CACHE_TTL: float = 300.0  # 5 minutes - extended from 60s to reduce DB queries


def _invalidate_bangumi_cache():
    global _bangumi_cache, _bangumi_cache_time
    _bangumi_cache = None
    _bangumi_cache_time = 0


class BangumiDatabase:
    def __init__(self, session: Session):
        self.session = session

    def _is_duplicate(self, data: Bangumi) -> bool:
        """Check if a bangumi rule already exists based on title_raw and group_name."""
        statement = select(Bangumi).where(
            and_(
                Bangumi.title_raw == data.title_raw,
                Bangumi.group_name == data.group_name,
            )
        )
        result = self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    def add(self, data: Bangumi) -> bool:
        if self._is_duplicate(data):
            logger.debug(
                f"[Database] Skipping duplicate: {data.official_title} ({data.group_name})"
            )
            return False
        self.session.add(data)
        self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Insert {data.official_title} into database.")
        return True

    def add_all(self, datas: list[Bangumi]) -> int:
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
            result = self.session.execute(statement)
            existing = set(result.all())
        else:
            existing = set()

        # Filter out duplicates
        to_add = [d for d in datas if (d.title_raw, d.group_name) not in existing]

        # Also deduplicate within the batch itself
        seen = set()
        unique_to_add = []
        for d in to_add:
            key = (d.title_raw, d.group_name)
            if key not in seen:
                seen.add(key)
                unique_to_add.append(d)

        if not unique_to_add:
            logger.debug(
                f"[Database] All {len(datas)} bangumi already exist, skipping."
            )
            return 0

        self.session.add_all(unique_to_add)
        self.session.commit()
        _invalidate_bangumi_cache()
        skipped = len(datas) - len(unique_to_add)
        if skipped > 0:
            logger.debug(
                f"[Database] Insert {len(unique_to_add)} bangumi, skipped {skipped} duplicates."
            )
        else:
            logger.debug(
                f"[Database] Insert {len(unique_to_add)} bangumi into database."
            )
        return len(unique_to_add)

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
        if (
            _bangumi_cache is not None
            and (now - _bangumi_cache_time) < _BANGUMI_CACHE_TTL
        ):
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

        # Build index for O(1) lookup after regex match
        title_index = {m.title_raw: m for m in match_datas}

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
                title_raw = match.group(0)
                match_data = title_index[title_raw]
                if rss_link not in match_data.rss_link and title_raw not in rss_updated:
                    match_data.rss_link += f",{rss_link}"
                    match_data.added = False
                    rss_updated.add(title_raw)
            else:
                unmatched.append(torrent)
        # Batch commit all rss_link updates
        if rss_updated:
            self.session.commit()
            _invalidate_bangumi_cache()
            logger.debug(
                f"[Database] Batch updated rss_link for {len(rss_updated)} bangumi."
            )
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
        result = self.session.execute(statement)
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
            result = self.session.execute(statement)
            bangumi = result.scalars().first()
            if bangumi:
                return bangumi

        return None

    def get_needs_review(self) -> list[Bangumi]:
        """Get all bangumi that need review for offset mismatch."""
        statement = select(Bangumi).where(
            and_(
                Bangumi.needs_review == True,  # noqa: E712
                Bangumi.deleted == false(),
            )
        )
        result = self.session.execute(statement)
        return list(result.scalars().all())

    def get_active_for_scan(self) -> list[Bangumi]:
        """Get all active (non-deleted, non-archived) bangumi for offset scanning."""
        statement = select(Bangumi).where(
            and_(
                Bangumi.deleted == false(),
                Bangumi.archived == false(),
            )
        )
        result = self.session.execute(statement)
        return list(result.scalars().all())

    def set_needs_review(
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
        bangumi = self.session.get(Bangumi, _id)
        if not bangumi:
            return False
        bangumi.needs_review = True
        bangumi.needs_review_reason = reason
        bangumi.suggested_season_offset = suggested_season_offset
        bangumi.suggested_episode_offset = suggested_episode_offset
        self.session.add(bangumi)
        self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(
            f"[Database] Marked bangumi id {_id} as needs_review: {reason} "
            f"(suggested: season={suggested_season_offset}, episode={suggested_episode_offset})"
        )
        return True

    def clear_needs_review(self, _id: int) -> bool:
        """Clear the needs_review flag and suggested offsets for a bangumi."""
        bangumi = self.session.get(Bangumi, _id)
        if not bangumi:
            return False
        bangumi.needs_review = False
        bangumi.needs_review_reason = None
        bangumi.suggested_season_offset = None
        bangumi.suggested_episode_offset = None
        self.session.add(bangumi)
        self.session.commit()
        _invalidate_bangumi_cache()
        logger.debug(f"[Database] Cleared needs_review for bangumi id {_id}")
        return True

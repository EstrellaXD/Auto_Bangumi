"""Background scanner for detecting season/episode offset mismatches."""

import logging

from module.conf import settings
from module.database import Database
from module.models import Bangumi
from module.notification.events import OffsetReviewEvent
from module.parser.analyser.offset_detector import detect_offset_mismatch
from module.parser.analyser.selector import parse_configured_release_title
from module.parser.analyser.tmdb_parser import tmdb_parser
from module.parser.release_policy import is_offset_signal

logger = logging.getLogger(__name__)


class OffsetScanner:
    """Periodically scan bangumi for season/episode mismatches with TMDB."""

    async def scan_all(self) -> list[OffsetReviewEvent]:
        """Scan all active bangumi for offset mismatches.

        Returns:
            One event per bangumi flagged for review.
        """
        logger.info("Starting offset scan...")

        async with Database() as db:
            bangumi_list = await db.bangumi.get_active_for_scan()

        if not bangumi_list:
            logger.debug("No active bangumi to scan.")
            return []

        events: list[OffsetReviewEvent] = []
        for bangumi in bangumi_list:
            try:
                event = await self._check_bangumi(bangumi)
                if event is not None:
                    events.append(event)
            except Exception as e:
                logger.warning(f"Error checking {bangumi.official_title}: {e}")

        logger.info(f"Scan complete. Flagged {len(events)} bangumi for review.")
        return events

    async def _check_bangumi(self, bangumi: Bangumi) -> OffsetReviewEvent | None:
        """Check a single bangumi for offset mismatch.

        Args:
            bangumi: The bangumi to check.

        Returns:
            An event describing the flag if the bangumi was flagged for
            review, None otherwise.
        """
        # Skip if already needs review
        if bangumi.needs_review:
            logger.debug(f"Skipping {bangumi.official_title}: already needs review")
            return None

        # OVA/OAD/SP are persisted as Bangumi for library compatibility, but
        # they are not weekly episode streams and must never drive offsets.
        if bangumi.episode_type != "episode":
            logger.debug(
                "Skipping %s: episode_type=%s",
                bangumi.official_title,
                bangumi.episode_type,
            )
            return None

        # Skip if user has already configured offsets
        if bangumi.season_offset != 0 or bangumi.episode_offset != 0:
            logger.debug(f"Skipping {bangumi.official_title}: has configured offsets")
            return None

        # Get TMDB info
        language = settings.rss_parser.language
        tmdb_info = await tmdb_parser(bangumi.official_title, language)

        if not tmdb_info:
            logger.debug(f"Skipping {bangumi.official_title}: no TMDB info")
            return None

        # Get the real latest parsed episode from this bangumi's torrent records,
        # instead of guessing. No torrents parsed yet means no signal to act on.
        parsed_episode = await self._get_latest_parsed_episode(bangumi.id)
        if parsed_episode is None:
            logger.debug(f"Skipping {bangumi.official_title}: no parsed episode data")
            return None

        # Detect mismatch
        suggestion = detect_offset_mismatch(
            parsed_season=bangumi.season,
            parsed_episode=parsed_episode,
            tmdb_info=tmdb_info,
        )

        if suggestion and suggestion.confidence in ("high", "medium"):
            async with Database() as db:
                await db.bangumi.set_needs_review(
                    bangumi.id,
                    suggestion.reason,
                    suggested_season_offset=suggestion.season_offset,
                    suggested_episode_offset=suggestion.episode_offset,
                )
            logger.info(
                f"Flagged {bangumi.official_title} for review: {suggestion.reason} "
                f"(suggested: season={suggestion.season_offset}, episode={suggestion.episode_offset})"
            )
            return OffsetReviewEvent(
                official_title=bangumi.official_title, reason=suggestion.reason
            )

        return None

    async def _get_latest_parsed_episode(self, bangumi_id: int) -> int | None:
        """从 Torrent 表解析该番剧已知的最新集数，作为真实信号使用。

        Returns:
            解析到的最大集数；若没有种子记录或均无法解析出集数则返回 None。
        """
        async with Database() as db:
            torrents = await db.torrent.search_by_bangumi_id(bangumi_id)

        latest: int | None = None
        for torrent in torrents:
            release = parse_configured_release_title(torrent.name)
            if release is None or not is_offset_signal(release):
                continue
            episode = release.episode
            # ``is_offset_signal`` guarantees this at runtime; retain the local
            # guard so static type checking can narrow ``int | float | None``.
            if type(episode) is not int:
                continue
            if latest is None or episode > latest:
                latest = episode
        return latest

    async def check_single(self, bangumi_id: int) -> bool:
        """Check a single bangumi by ID.

        Args:
            bangumi_id: The ID of the bangumi to check.

        Returns:
            True if flagged for review, False otherwise.
        """
        async with Database() as db:
            bangumi = await db.bangumi.search_id(bangumi_id)

        if not bangumi:
            logger.warning(f"Bangumi {bangumi_id} not found")
            return False

        return await self._check_bangumi(bangumi) is not None

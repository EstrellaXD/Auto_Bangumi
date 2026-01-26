"""Background scanner for detecting season/episode offset mismatches."""

import logging

from module.conf import settings
from module.database import Database
from module.models import Bangumi
from module.parser.analyser.offset_detector import detect_offset_mismatch
from module.parser.analyser.tmdb_parser import tmdb_parser

logger = logging.getLogger(__name__)


class OffsetScanner:
    """Periodically scan bangumi for season/episode mismatches with TMDB."""

    async def scan_all(self) -> int:
        """Scan all active bangumi for offset mismatches.

        Returns:
            Number of bangumi flagged for review.
        """
        logger.info("[OffsetScanner] Starting offset scan...")

        with Database() as db:
            bangumi_list = db.bangumi.get_active_for_scan()

        if not bangumi_list:
            logger.debug("[OffsetScanner] No active bangumi to scan.")
            return 0

        flagged_count = 0
        for bangumi in bangumi_list:
            try:
                if await self._check_bangumi(bangumi):
                    flagged_count += 1
            except Exception as e:
                logger.warning(
                    f"[OffsetScanner] Error checking {bangumi.official_title}: {e}"
                )

        logger.info(
            f"[OffsetScanner] Scan complete. Flagged {flagged_count} bangumi for review."
        )
        return flagged_count

    async def _check_bangumi(self, bangumi: Bangumi) -> bool:
        """Check a single bangumi for offset mismatch.

        Args:
            bangumi: The bangumi to check.

        Returns:
            True if flagged for review, False otherwise.
        """
        # Skip if already needs review
        if bangumi.needs_review:
            logger.debug(
                f"[OffsetScanner] Skipping {bangumi.official_title}: already needs review"
            )
            return False

        # Skip if user has already configured offsets
        if bangumi.season_offset != 0 or bangumi.episode_offset != 0:
            logger.debug(
                f"[OffsetScanner] Skipping {bangumi.official_title}: has configured offsets"
            )
            return False

        # Get TMDB info
        language = settings.rss_parser.language
        tmdb_info = await tmdb_parser(bangumi.official_title, language)

        if not tmdb_info:
            logger.debug(
                f"[OffsetScanner] Skipping {bangumi.official_title}: no TMDB info"
            )
            return False

        # Get latest episode for this bangumi (use season as proxy since we don't track episodes)
        # For now, we'll check based on the bangumi's season
        parsed_episode = 1  # Default to episode 1 for season-based detection

        # Detect mismatch
        suggestion = detect_offset_mismatch(
            parsed_season=bangumi.season,
            parsed_episode=parsed_episode,
            tmdb_info=tmdb_info,
        )

        if suggestion and suggestion.confidence in ("high", "medium"):
            with Database() as db:
                db.bangumi.set_needs_review(
                    bangumi.id,
                    suggestion.reason,
                    suggested_season_offset=suggestion.season_offset,
                    suggested_episode_offset=suggestion.episode_offset,
                )
            logger.info(
                f"[OffsetScanner] Flagged {bangumi.official_title} for review: {suggestion.reason} "
                f"(suggested: season={suggestion.season_offset}, episode={suggestion.episode_offset})"
            )
            return True

        return False

    async def check_single(self, bangumi_id: int) -> bool:
        """Check a single bangumi by ID.

        Args:
            bangumi_id: The ID of the bangumi to check.

        Returns:
            True if flagged for review, False otherwise.
        """
        with Database() as db:
            bangumi = db.bangumi.search_id(bangumi_id)

        if not bangumi:
            logger.warning(f"[OffsetScanner] Bangumi {bangumi_id} not found")
            return False

        return await self._check_bangumi(bangumi)

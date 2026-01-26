"""Offset detector for detecting season/episode mismatches with TMDB data."""

import logging
from dataclasses import dataclass
from typing import Literal

from module.parser.analyser.tmdb_parser import TMDBInfo

logger = logging.getLogger(__name__)


@dataclass
class OffsetSuggestion:
    """Suggested offsets to align RSS parsed data with TMDB."""

    season_offset: int
    episode_offset: int | None  # None means no episode offset needed
    reason: str
    confidence: Literal["high", "medium", "low"]


def detect_offset_mismatch(
    parsed_season: int,
    parsed_episode: int,
    tmdb_info: TMDBInfo,
) -> OffsetSuggestion | None:
    """Detect if there's a mismatch between parsed season/episode and TMDB data.

    Uses air date gaps to detect "virtual seasons" - when TMDB has 1 season but
    subtitle groups split it into S1/S2 based on broadcast breaks (>6 months gap).

    Args:
        parsed_season: Season number parsed from RSS/torrent name
        parsed_episode: Episode number parsed from RSS/torrent name
        tmdb_info: TMDB information for the anime

    Returns:
        OffsetSuggestion if a mismatch is detected, None otherwise

    Note:
        When only season_offset is needed (simple season mismatch), episode_offset
        will be None. Episode offset is only set when there's a virtual season split
        where episodes need to be renumbered (e.g., RSS S2E01 → TMDB S1E25).
    """
    if not tmdb_info or not tmdb_info.last_season:
        return None

    suggested_season_offset = 0
    suggested_episode_offset: int | None = None  # Only set when virtual season detected
    reasons = []
    confidence: Literal["high", "medium", "low"] = "high"

    # Check season mismatch
    # If parsed season exceeds TMDB's total seasons, suggest mapping to last season
    if parsed_season > tmdb_info.last_season:
        suggested_season_offset = tmdb_info.last_season - parsed_season
        target_season = parsed_season + suggested_season_offset

        # Check if this season has virtual season breakpoints (detected from air date gaps)
        if (
            tmdb_info.virtual_season_starts
            and target_season in tmdb_info.virtual_season_starts
        ):
            vs_starts = tmdb_info.virtual_season_starts[target_season]
            # Calculate which virtual season the parsed_season maps to
            # e.g., if vs_starts = [1, 29] and parsed_season = 2, we're in the 2nd virtual season
            virtual_season_index = (
                parsed_season - target_season
            )  # 0-indexed from target

            if virtual_season_index > 0 and virtual_season_index < len(vs_starts):
                # Only set episode offset for 2nd+ virtual season (index > 0)
                # First virtual season (index 0) starts at episode 1, no offset needed
                suggested_episode_offset = vs_starts[virtual_season_index] - 1
                reasons.append(
                    f"RSS显示S{parsed_season}，但TMDB只有{tmdb_info.last_season}季"
                    f"（检测到第{virtual_season_index + 1}部分从第{vs_starts[virtual_season_index]}集开始，"
                    f"建议集数偏移+{suggested_episode_offset}）"
                )
                logger.debug(
                    f"[OffsetDetector] Virtual season detected: S{parsed_season} maps to "
                    f"TMDB S{target_season} starting at episode {vs_starts[virtual_season_index]}"
                )
            else:
                # Simple season mismatch, no episode offset needed
                reasons.append(
                    f"RSS显示S{parsed_season}，但TMDB只有{tmdb_info.last_season}季"
                    f"（建议季度偏移{suggested_season_offset}，无需调整集数）"
                )
        else:
            # Simple season mismatch, no episode offset needed
            reasons.append(
                f"RSS显示S{parsed_season}，但TMDB只有{tmdb_info.last_season}季"
                f"（建议季度偏移{suggested_season_offset}，无需调整集数）"
            )

        logger.debug(
            f"[OffsetDetector] Season mismatch: parsed S{parsed_season}, "
            f"TMDB has {tmdb_info.last_season} seasons, suggesting offset {suggested_season_offset}"
        )

    # Check episode range for target season
    target_season = parsed_season + suggested_season_offset
    if tmdb_info.season_episode_counts:
        season_ep_count = tmdb_info.season_episode_counts.get(target_season, 0)
        adjusted_episode = parsed_episode + (suggested_episode_offset or 0)

        if season_ep_count > 0 and adjusted_episode > season_ep_count:
            # Episode exceeds the count for this season
            if tmdb_info.series_status == "Returning Series":
                confidence = "medium"
                reasons.append(
                    f"调整后集数{adjusted_episode}超出TMDB该季的{season_ep_count}集"
                    f"（正在放送中，TMDB可能未更新）"
                )
            else:
                reasons.append(
                    f"调整后集数{adjusted_episode}超出TMDB该季的{season_ep_count}集"
                )

            logger.debug(
                f"[OffsetDetector] Episode range issue: adjusted E{adjusted_episode}, "
                f"TMDB S{target_season} has {season_ep_count} episodes"
            )

    # Only return suggestion if there's actually a mismatch
    if reasons:
        return OffsetSuggestion(
            season_offset=suggested_season_offset,
            episode_offset=suggested_episode_offset,
            reason="; ".join(reasons),
            confidence=confidence,
        )

    return None

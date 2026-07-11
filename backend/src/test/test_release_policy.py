from dataclasses import replace

import pytest

from module.parser.analyser.tokenizer.result import (
    MediaType,
    ParsedRelease,
    ReleaseKind,
)
from module.parser.release_policy import (
    PersistenceTarget,
    bangumi_episode_type,
    has_release_evidence,
    is_offset_signal,
    is_weak_title_only,
    normalized_season,
    persistence_target,
    preference_identity,
    preference_revision,
)


def _release(
    *,
    raw: str = "[Group] Anime - 01 [1080p]",
    group: str | None = "Group",
    resolution: str | None = None,
    episode: int | float | None = 1,
    season: int | None = None,
    media_type: MediaType = MediaType.EPISODE,
    release_kind: ReleaseKind = ReleaseKind.SINGLE,
) -> ParsedRelease:
    base = ParsedRelease(raw=raw, title_en="Anime")
    return replace(
        base,
        group=group,
        resolution=resolution,
        episode=episode,
        season=season,
        media_type=media_type,
        release_kind=release_kind,
    )


def test_persistence_policy_separates_parsing_from_admission() -> None:
    assert persistence_target(_release()) is PersistenceTarget.BANGUMI
    assert (
        persistence_target(_release(media_type=MediaType.MOVIE, episode=None))
        is PersistenceTarget.MOVIE
    )
    assert persistence_target(_release(media_type=MediaType.PV)) is None
    assert (
        persistence_target(
            _release(
                media_type=MediaType.MOVIE,
                episode=None,
                release_kind=ReleaseKind.COLLECTION,
            )
        )
        is None
    )


@pytest.mark.parametrize("release_kind", list(ReleaseKind)[1:])
def test_non_single_releases_are_not_persisted_by_default(
    release_kind: ReleaseKind,
) -> None:
    assert persistence_target(_release(release_kind=release_kind)) is None


@pytest.mark.parametrize(
    "media_type", (MediaType.PV, MediaType.OPENING, MediaType.ENDING)
)
def test_non_content_video_kinds_are_not_persisted(media_type: MediaType) -> None:
    assert persistence_target(_release(media_type=media_type)) is None


@pytest.mark.parametrize(
    "media_type", (MediaType.OVA, MediaType.OAD, MediaType.SPECIAL)
)
def test_special_media_projects_to_bangumi(media_type: MediaType) -> None:
    release = _release(media_type=media_type)

    assert persistence_target(release) is PersistenceTarget.BANGUMI
    assert bangumi_episode_type(release) == "special"
    assert normalized_season(release) == 0


def test_title_only_requires_release_evidence() -> None:
    bare = _release(
        raw="Random title",
        group=None,
        resolution=None,
        episode=None,
        media_type=MediaType.UNKNOWN,
    )
    assert is_weak_title_only(bare)
    assert not is_weak_title_only(_release(episode=None, media_type=MediaType.UNKNOWN))
    assert persistence_target(bare) is None
    assert (
        persistence_target(_release(episode=None, media_type=MediaType.UNKNOWN))
        is PersistenceTarget.BANGUMI
    )


@pytest.mark.parametrize(
    "release",
    (
        _release(group="Group", episode=None, media_type=MediaType.UNKNOWN),
        _release(
            group=None,
            resolution="1080p",
            episode=None,
            media_type=MediaType.UNKNOWN,
        ),
    ),
)
def test_strong_metadata_counts_as_release_evidence(release: ParsedRelease) -> None:
    assert has_release_evidence(release)


def test_preference_identity_keeps_season_and_media_dimensions() -> None:
    episode = _release(season=2)
    ova = _release(media_type=MediaType.OVA, season=None)

    assert preference_identity(episode) == (MediaType.EPISODE, 2, 1)
    assert preference_identity(ova) == (MediaType.OVA, 0, 1)
    assert preference_identity(episode) != preference_identity(ova)


def test_preference_identity_can_inherit_matched_bangumi_season() -> None:
    implicit = _release(season=None)
    special = _release(media_type=MediaType.OVA, season=None)

    assert preference_identity(implicit, default_season=2) == (
        MediaType.EPISODE,
        2,
        1,
    )
    assert preference_identity(special, default_season=2) == (
        MediaType.OVA,
        0,
        1,
    )


def test_half_episode_has_identity_but_never_drives_offset() -> None:
    half = _release(episode=12.5, season=2)

    assert preference_identity(half) == (MediaType.EPISODE, 2, 12.5)
    assert is_offset_signal(half) is False


def test_non_single_or_unnumbered_release_has_no_preference_identity() -> None:
    assert preference_identity(_release(release_kind=ReleaseKind.RANGE)) is None
    assert preference_identity(_release(episode=None)) is None
    assert preference_identity(_release(media_type=MediaType.PV)) is None


def test_preference_revision_defaults_to_one_and_uses_explicit_version() -> None:
    assert preference_revision(_release()) == 1
    assert preference_revision(replace(_release(), version=3)) == 3


def test_offset_signal_is_strictly_positive_integer_weekly_episode() -> None:
    assert is_offset_signal(_release()) is True
    assert is_offset_signal(_release(episode=12.5)) is False
    assert is_offset_signal(_release(media_type=MediaType.OVA)) is False
    assert is_offset_signal(_release(release_kind=ReleaseKind.RANGE)) is False
    assert is_offset_signal(_release(episode=0)) is False
    assert is_offset_signal(_release(episode=True)) is False

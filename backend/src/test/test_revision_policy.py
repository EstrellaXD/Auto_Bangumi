from module.manager.revision_policy import (
    is_strict_upgrade,
    parse_revision_identity,
    replacement_staged_path,
    same_release_identity,
)

V1 = "[ANi] 尼古喵喵 - 01 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
V2 = "[ANi] 尼古喵喵 - 01 [V2][1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"


def test_mikan_classic_v2_is_a_strict_upgrade():
    old = parse_revision_identity(V1, bangumi_id=42, default_season=1)
    new = parse_revision_identity(V2, bangumi_id=42, default_season=1)

    assert old is not None
    assert new is not None
    assert old.revision == 1
    assert new.revision == 2
    assert same_release_identity(old, new)
    assert is_strict_upgrade(old, new)


def test_cross_group_or_resolution_is_not_a_strict_upgrade():
    old = parse_revision_identity(V1, bangumi_id=42, default_season=1)
    other_group = parse_revision_identity(
        V2.replace("[ANi]", "[Other]"), bangumi_id=42, default_season=1
    )
    other_resolution = parse_revision_identity(
        V2.replace("1080P", "720P"), bangumi_id=42, default_season=1
    )

    assert old is not None
    assert other_group is not None
    assert other_resolution is not None
    assert not is_strict_upgrade(old, other_group)
    assert not is_strict_upgrade(old, other_resolution)


def test_missing_bangumi_group_or_resolution_is_ineligible():
    assert parse_revision_identity(V2, bangumi_id=None, default_season=1) is None
    assert (
        parse_revision_identity(
            "尼古喵喵 - 01 [V2][1080P].mp4",
            bangumi_id=42,
            default_season=1,
        )
        is None
    )


def test_staged_path_is_deterministic_and_keeps_extension():
    assert (
        replacement_staged_path(
            "subdir/尼古喵喵 S01E01.mp4", old_task_id="abcdef123456", old_revision=1
        )
        == "subdir/尼古喵喵 S01E01.ab-replaced-v1-abcdef12.mp4"
    )

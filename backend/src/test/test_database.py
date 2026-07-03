import json

from module.database.bangumi import BangumiDatabase
from module.database.rss import RSSDatabase
from module.database.torrent import TorrentDatabase
from module.models import Bangumi, RSSItem, Torrent


async def _ensure_bangumi(session, bangumi_id: int):
    """确保 bangumi 表中存在指定 id 的记录，满足外键约束。"""
    if await session.get(Bangumi, bangumi_id) is None:
        session.add(
            Bangumi(
                id=bangumi_id,
                official_title=f"Stub Anime {bangumi_id}",
                title_raw=f"Stub {bangumi_id}",
                group_name="TestGroup",
                dpi="1080p",
                source="Web",
                subtitle="CHT",
                rss_link=f"stub_{bangumi_id}",
            )
        )
        await session.commit()


async def test_bangumi_database(db_session):
    test_data = Bangumi(
        official_title="无职转生，到了异世界就拿出真本事",
        year="2021",
        title_raw="Mushoku Tensei",
        season=1,
        season_raw="",
        group_name="Lilith-Raws",
        dpi="1080p",
        source="Baha",
        subtitle="CHT",
        eps_collect=False,
        offset=0,
        filter="720p,\\d+-\\d+",
        rss_link="test",
        poster_link="/test/test.jpg",
        added=False,
        rule_name=None,
        save_path="downloads/无职转生，到了异世界就拿出真本事/Season 1",
        deleted=False,
    )
    db = BangumiDatabase(db_session)

    # insert
    await db.add(test_data)
    result = await db.search_id(1)
    assert result is not None
    assert result.official_title == test_data.official_title

    # update
    test_data.official_title = "无职转生，到了异世界就拿出真本事II"
    await db.update(test_data)
    result = await db.search_id(1)
    assert result is not None
    assert result.official_title == test_data.official_title

    # search poster
    poster = await db.match_poster("无职转生，到了异世界就拿出真本事II (2021)")
    assert poster == "/test/test.jpg"

    # match torrent
    result = await db.match_torrent(
        "[Lilith-Raws] 无职转生，到了异世界就拿出真本事 / Mushoku Tensei - 11 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    )
    assert result is not None
    assert result.official_title == "无职转生，到了异世界就拿出真本事II"

    # delete
    await db.delete_one(1)
    result = await db.search_id(1)
    assert result is None


async def test_torrent_database(db_session):
    test_data = Torrent(
        name="[Sub Group]test S02 01 [720p].mkv",
        url="https://test.com/test.mkv",
    )
    db = TorrentDatabase(db_session)

    # insert
    await db.add(test_data)
    result = await db.search(1)
    assert result is not None
    assert result.name == test_data.name

    # update
    test_data.downloaded = True
    await db.update(test_data)
    result = await db.search(1)
    assert result is not None
    assert result.downloaded is True


async def test_rss_database(db_session):
    rss_url = "https://test.com/test.xml"
    db = RSSDatabase(db_session)

    await db.add(RSSItem(url=rss_url, name="Test RSS"))
    result = await db.search_id(1)
    assert result is not None
    assert result.url == rss_url


# ---------------------------------------------------------------------------
# TorrentDatabase qb_hash methods
# ---------------------------------------------------------------------------


async def test_torrent_search_by_qb_hash(db_session):
    """Test searching torrent by qBittorrent hash."""
    db = TorrentDatabase(db_session)

    # Create torrent with qb_hash
    torrent = Torrent(
        name="[SubGroup] Test Anime - 01 [1080p].mkv",
        url="https://example.com/torrent1",
        qb_hash="abc123def456",
    )
    await db.add(torrent)

    # Search by qb_hash
    result = await db.search_by_qb_hash("abc123def456")
    assert result is not None
    assert result.name == torrent.name
    assert result.qb_hash == "abc123def456"


async def test_torrent_search_by_qb_hash_not_found(db_session):
    """Test searching non-existent qb_hash returns None."""
    db = TorrentDatabase(db_session)

    result = await db.search_by_qb_hash("nonexistent_hash")
    assert result is None


async def test_torrent_search_by_url(db_session):
    """Test searching torrent by URL."""
    db = TorrentDatabase(db_session)

    url = "https://mikanani.me/Download/torrent123.torrent"
    torrent = Torrent(
        name="[SubGroup] Test Anime - 02 [1080p].mkv",
        url=url,
    )
    await db.add(torrent)

    # Search by URL
    result = await db.search_by_url(url)
    assert result is not None
    assert result.url == url
    assert result.name == torrent.name


async def test_torrent_search_by_url_not_found(db_session):
    """Test searching non-existent URL returns None."""
    db = TorrentDatabase(db_session)

    result = await db.search_by_url("https://nonexistent.com/torrent.torrent")
    assert result is None


async def test_torrent_update_qb_hash(db_session):
    """Test updating qb_hash for existing torrent."""
    db = TorrentDatabase(db_session)

    # Create torrent without qb_hash
    torrent = Torrent(
        name="[SubGroup] Test Anime - 03 [1080p].mkv",
        url="https://example.com/torrent3",
    )
    await db.add(torrent)
    assert torrent.qb_hash is None

    # Update qb_hash
    success = await db.update_qb_hash(torrent.id, "new_hash_value")
    assert success is True

    # Verify update
    result = await db.search(torrent.id)
    assert result is not None
    assert result.qb_hash == "new_hash_value"


async def test_torrent_update_qb_hash_nonexistent(db_session):
    """Test updating qb_hash for non-existent torrent returns False."""
    db = TorrentDatabase(db_session)

    success = await db.update_qb_hash(99999, "some_hash")
    assert success is False


async def test_torrent_with_bangumi_id(db_session):
    """Test torrent with bangumi_id for offset lookup."""
    db = TorrentDatabase(db_session)

    # 父记录满足外键约束
    await _ensure_bangumi(db_session, 42)

    # Create torrent linked to a bangumi
    torrent = Torrent(
        name="[SubGroup] Test Anime - 04 [1080p].mkv",
        url="https://example.com/torrent4",
        bangumi_id=42,
        qb_hash="hash_for_bangumi_42",
    )
    await db.add(torrent)

    # Search and verify bangumi_id is preserved
    result = await db.search_by_qb_hash("hash_for_bangumi_42")
    assert result is not None
    assert result.bangumi_id == 42


async def test_torrent_qb_hash_index_efficient(db_session):
    """Test that qb_hash lookups work correctly with multiple torrents."""
    db = TorrentDatabase(db_session)

    # Add multiple torrents
    torrents = [
        Torrent(
            name=f"Torrent {i}", url=f"https://example.com/{i}", qb_hash=f"hash_{i}"
        )
        for i in range(10)
    ]
    await db.add_all(torrents)

    # Verify we can find specific torrents by hash
    result = await db.search_by_qb_hash("hash_5")
    assert result is not None
    assert result.name == "Torrent 5"

    result = await db.search_by_qb_hash("hash_9")
    assert result is not None
    assert result.name == "Torrent 9"

    # Non-existent hash
    result = await db.search_by_qb_hash("hash_100")
    assert result is None


# ============================================================
# Title Alias Tests - for mid-season naming change handling
# ============================================================


async def test_add_title_alias(db_session):
    """Test adding a title alias to an existing bangumi."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    await db.add(bangumi)
    bangumi_id = (await db.search_all())[0].id

    # Add an alias
    result = await db.add_title_alias(bangumi_id, "Test Anime Season 1")
    assert result is True

    # Verify alias was added
    updated = await db.search_id(bangumi_id)
    assert updated is not None
    assert updated.title_aliases is not None
    aliases = json.loads(updated.title_aliases)
    assert "Test Anime Season 1" in aliases


async def test_add_title_alias_duplicate(db_session):
    """Test that adding the same alias twice is a no-op."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    await db.add(bangumi)
    bangumi_id = (await db.search_all())[0].id

    # Add same alias twice
    await db.add_title_alias(bangumi_id, "Test Anime Season 1")
    result = await db.add_title_alias(bangumi_id, "Test Anime Season 1")
    assert result is False  # Second add should be a no-op


async def test_add_title_alias_same_as_title_raw(db_session):
    """Test that adding title_raw as alias is a no-op."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    await db.add(bangumi)
    bangumi_id = (await db.search_all())[0].id

    result = await db.add_title_alias(bangumi_id, "Test Anime S1")
    assert result is False


async def test_match_torrent_with_alias(db_session):
    """Test that match_torrent finds bangumi using aliases."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
        deleted=False,
    )
    await db.add(bangumi)
    bangumi_id = (await db.search_all())[0].id

    # Add alias
    await db.add_title_alias(bangumi_id, "Test Anime Season 1")

    # Match using title_raw
    result = await db.match_torrent("[TestGroup] Test Anime S1 - 01.mkv")
    assert result is not None
    assert result.official_title == "Test Anime"

    # Match using alias
    result = await db.match_torrent("[TestGroup] Test Anime Season 1 - 01.mkv")
    assert result is not None
    assert result.official_title == "Test Anime"


async def test_find_semantic_duplicate_same_official_title(db_session):
    """Test finding semantic duplicates with same official title."""
    db = BangumiDatabase(db_session)

    # Add first bangumi
    bangumi1 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren",
        group_name="LoliHouse",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test1",
    )
    await db.add(bangumi1)

    # Create a semantically similar bangumi (same anime, group changed naming)
    bangumi2 = Bangumi(
        official_title="Frieren",
        title_raw="Frieren Beyond Journey's End",  # Different title_raw
        group_name="LoliHouse&动漫国",  # Group changed mid-season
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test2",
    )

    # Should find semantic duplicate
    result = await db.find_semantic_duplicate(bangumi2)
    assert result is not None
    assert result.title_raw == "Sousou no Frieren"


async def test_find_semantic_duplicate_no_match_different_resolution(db_session):
    """Test that different resolution is NOT a semantic match."""
    db = BangumiDatabase(db_session)

    bangumi1 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren",
        group_name="LoliHouse",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test1",
    )
    await db.add(bangumi1)

    # Same anime but different resolution - should NOT be semantic duplicate
    bangumi2 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren 4K",
        group_name="LoliHouse",
        dpi="2160p",  # Different resolution
        source="Web",
        subtitle="CHT",
        rss_link="test2",
    )

    result = await db.find_semantic_duplicate(bangumi2)
    assert result is None


async def test_add_with_semantic_duplicate_creates_alias(db_session):
    """Test that adding a semantic duplicate creates an alias instead."""
    db = BangumiDatabase(db_session)

    # Add first bangumi
    bangumi1 = Bangumi(
        official_title="Frieren",
        title_raw="Sousou no Frieren",
        group_name="LoliHouse",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test1",
    )
    await db.add(bangumi1)
    initial_count = len(await db.search_all())
    assert initial_count == 1

    # Try to add semantic duplicate
    bangumi2 = Bangumi(
        official_title="Frieren",
        title_raw="Frieren Beyond Journey's End",
        group_name="LoliHouse&动漫国",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test2",
    )
    result = await db.add(bangumi2)
    assert result is False  # Should not add new entry

    # Count should still be 1
    final_count = len(await db.search_all())
    assert final_count == 1

    # But the new title_raw should be an alias
    original = (await db.search_all())[0]
    aliases = json.loads(original.title_aliases) if original.title_aliases else []
    assert "Frieren Beyond Journey's End" in aliases


async def test_add_same_title_new_entry_inherits_year(db_session):
    """A new entry for an already-known anime (same official_title, different
    group/quality so no semantic merge) must inherit the existing year, so both
    entries build the same save path (title (year)/Season N)."""
    db = BangumiDatabase(db_session)

    existing = Bangumi(
        official_title="躲在超市后门抽烟的两人",
        year="2026",
        title_raw="躲在超市后门抽烟的两人",
        group_name="樱都字幕组",
        dpi="1080p",
        source="Baha",
        subtitle="CHS",
        rss_link="test1",
    )
    await db.add(existing)

    new_entry = Bangumi(
        official_title="躲在超市后门抽烟的两人",
        year=None,
        title_raw="Super no Ura de Yani Suu Futari",
        group_name="Dynamis One",
        dpi="1080p",
        source="ABEMA",
        subtitle="JPSC",
        rss_link="test2",
    )
    result = await db.add(new_entry)

    assert result is True  # different group/source: a new entry, not a merge
    assert new_entry.year == "2026"


async def test_add_same_title_keeps_own_year(db_session):
    """An explicitly parsed year must not be overwritten by an existing entry's."""
    db = BangumiDatabase(db_session)

    await db.add(
        Bangumi(
            official_title="Frieren",
            year="2023",
            title_raw="Sousou no Frieren",
            group_name="LoliHouse",
            dpi="1080p",
            source="Web",
            subtitle="CHT",
            rss_link="test1",
        )
    )

    new_entry = Bangumi(
        official_title="Frieren",
        year="2024",
        title_raw="Frieren S2",
        group_name="OtherGroup",
        dpi="720p",
        source="Baha",
        subtitle="CHS",
        rss_link="test2",
    )
    result = await db.add(new_entry)

    assert result is True
    assert new_entry.year == "2024"


async def test_add_all_same_title_new_entries_inherit_year(db_session):
    """add_all() applies the same year inheritance as add()."""
    db = BangumiDatabase(db_session)

    await db.add(
        Bangumi(
            official_title="躲在超市后门抽烟的两人",
            year="2026",
            title_raw="躲在超市后门抽烟的两人",
            group_name="樱都字幕组",
            dpi="1080p",
            source="Baha",
            subtitle="CHS",
            rss_link="test1",
        )
    )

    new_entry = Bangumi(
        official_title="躲在超市后门抽烟的两人",
        year=None,
        title_raw="Super no Ura de Yani Suu Futari",
        group_name="Dynamis One",
        dpi="1080p",
        source="ABEMA",
        subtitle="JPSC",
        rss_link="test2",
    )
    added = await db.add_all([new_entry])

    assert added == 1
    assert new_entry.year == "2026"


async def test_add_all_semantic_duplicates_across_batch_all_merged_as_aliases(
    db_session,
):
    """add_all() must catch semantic duplicates for every item in a batch, not
    just the first (regression test for the N+1 batching fix)."""
    db = BangumiDatabase(db_session)

    for i in range(5):
        await db.add(
            Bangumi(
                official_title=f"Anime {i}",
                title_raw=f"Raw {i}",
                group_name="GroupA",
                dpi="1080p",
                source="Web",
                subtitle="CHT",
                rss_link=f"rss{i}",
            )
        )

    batch = [
        Bangumi(
            official_title=f"Anime {i}",
            title_raw=f"Raw {i} New",
            group_name="GroupA&GroupB",  # naming changed mid-season
            dpi="1080p",
            source="Web",
            subtitle="CHT",
            rss_link=f"rss{i}-new",
        )
        for i in range(5)
    ]

    added = await db.add_all(batch)

    assert added == 0  # every item merged as an alias, no new rows
    assert len(await db.search_all()) == 5
    for i in range(5):
        original = await db.search_official_title(f"Anime {i}")
        assert original is not None
        aliases = json.loads(original.title_aliases) if original.title_aliases else []
        assert f"Raw {i} New" in aliases


async def test_add_all_semantic_duplicate_lookup_uses_batched_query(
    db_session, db_engine
):
    """add_all() loads semantic-duplicate candidates in one batched SELECT
    instead of one find_semantic_duplicate() query per candidate."""
    from sqlalchemy import event

    db = BangumiDatabase(db_session)

    for i in range(5):
        await db.add(
            Bangumi(
                official_title=f"Anime {i}",
                title_raw=f"Raw {i}",
                group_name="GroupA",
                dpi="1080p",
                source="Web",
                subtitle="CHT",
                rss_link=f"rss{i}",
            )
        )

    batch = [
        Bangumi(
            official_title=f"Anime {i}",
            title_raw=f"Raw {i} New",
            group_name="GroupA&GroupB",
            dpi="1080p",
            source="Web",
            subtitle="CHT",
            rss_link=f"rss{i}-new",
        )
        for i in range(5)
    ]

    select_statements = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        if statement.strip().upper().startswith("SELECT") and "bangumi" in statement:
            select_statements.append(statement)

    event.listen(db_engine.sync_engine, "before_cursor_execute", _record)
    try:
        await db.add_all(batch)
    finally:
        event.remove(db_engine.sync_engine, "before_cursor_execute", _record)

    # Exactly one SELECT for the exact-duplicate check plus one for the
    # semantic-duplicate candidates: O(1), not one per batch item (would be
    # 1 + 5 = 6 before the fix).
    assert len(select_statements) == 2


class TestDeleteByBangumiId:
    """Tests for TorrentDatabase.delete_by_bangumi_id."""

    async def test_deletes_matching_torrents(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 10)
        for i in range(3):
            await db.add(
                Torrent(
                    name=f"torrent_{i}", url=f"https://example.com/{i}", bangumi_id=10
                )
            )
        assert len(await db.search_all()) == 3

        count = await db.delete_by_bangumi_id(10)
        assert count == 3
        assert len(await db.search_all()) == 0

    async def test_leaves_other_bangumi_torrents(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 20)
        await _ensure_bangumi(db_session, 30)
        await db.add(
            Torrent(name="keep", url="https://example.com/keep", bangumi_id=20)
        )
        await db.add(
            Torrent(name="delete", url="https://example.com/delete", bangumi_id=30)
        )

        count = await db.delete_by_bangumi_id(30)
        assert count == 1
        remaining = await db.search_all()
        assert len(remaining) == 1
        assert remaining[0].name == "keep"

    async def test_no_match_returns_zero(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 5)
        await db.add(
            Torrent(name="unrelated", url="https://example.com/1", bangumi_id=5)
        )

        count = await db.delete_by_bangumi_id(999)
        assert count == 0
        assert len(await db.search_all()) == 1

    async def test_skips_null_bangumi_id(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 7)
        await db.add(
            Torrent(name="orphan", url="https://example.com/orphan", bangumi_id=None)
        )
        await db.add(
            Torrent(name="target", url="https://example.com/target", bangumi_id=7)
        )

        count = await db.delete_by_bangumi_id(7)
        assert count == 1
        remaining = await db.search_all()
        assert len(remaining) == 1
        assert remaining[0].bangumi_id is None

    async def test_check_new_finds_urls_after_cleanup(self, db_session):
        """Core scenario: after deleting torrent records, check_new should treat those URLs as new."""
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 42)
        await db.add(Torrent(name="ep01", url="https://mikan.me/t/001", bangumi_id=42))
        await db.add(Torrent(name="ep02", url="https://mikan.me/t/002", bangumi_id=42))

        # Before cleanup: check_new filters them out
        incoming = [Torrent(name="ep01", url="https://mikan.me/t/001")]
        assert await db.check_new(incoming) == []

        # After cleanup: same URLs are now "new"
        await db.delete_by_bangumi_id(42)
        new = await db.check_new(incoming)
        assert len(new) == 1
        assert new[0].url == "https://mikan.me/t/001"


class TestSearchByBangumiId:
    """Tests for TorrentDatabase.search_by_bangumi_id."""

    async def test_returns_matching_torrents(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 11)
        await db.add(
            Torrent(name="ep01", url="https://example.com/ep01", bangumi_id=11)
        )
        await db.add(
            Torrent(name="ep02", url="https://example.com/ep02", bangumi_id=11)
        )

        torrents = await db.search_by_bangumi_id(11)
        assert {t.name for t in torrents} == {"ep01", "ep02"}

    async def test_excludes_other_bangumi_torrents(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 21)
        await _ensure_bangumi(db_session, 22)
        await db.add(
            Torrent(name="keep", url="https://example.com/keep", bangumi_id=21)
        )
        await db.add(
            Torrent(name="other", url="https://example.com/other", bangumi_id=22)
        )

        torrents = await db.search_by_bangumi_id(21)
        assert [t.name for t in torrents] == ["keep"]

    async def test_no_match_returns_empty_list(self, db_session):
        db = TorrentDatabase(db_session)
        assert await db.search_by_bangumi_id(999) == []


class TestApplyOffset:
    """Tests for BangumiDatabase.apply_offset."""

    async def test_copies_suggested_offsets_into_live_offsets_and_clears_review(
        self, db_session
    ):
        db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Apply Offset Anime",
            title_raw="Apply Offset Anime Raw",
            group_name="TestGroup",
            rss_link="r",
            needs_review=True,
            needs_review_reason="mismatch detected",
            suggested_season_offset=-1,
            suggested_episode_offset=12,
        )
        db_session.add(bangumi)
        await db_session.commit()

        result = await db.apply_offset(bangumi.id)
        assert result is True

        updated = await db.search_id(bangumi.id)
        assert updated is not None
        assert updated.season_offset == -1
        assert updated.episode_offset == 12
        assert updated.needs_review is False
        assert updated.needs_review_reason is None
        assert updated.suggested_season_offset is None
        assert updated.suggested_episode_offset is None

    async def test_leaves_episode_offset_untouched_when_no_episode_suggestion(
        self, db_session
    ):
        """episode_offset suggestion of None means "no change needed", not "reset to 0"."""
        db = BangumiDatabase(db_session)
        bangumi = Bangumi(
            official_title="Season Only Anime",
            title_raw="Season Only Anime Raw",
            group_name="TestGroup",
            rss_link="r",
            episode_offset=3,
            needs_review=True,
            suggested_season_offset=-1,
            suggested_episode_offset=None,
        )
        db_session.add(bangumi)
        await db_session.commit()

        await db.apply_offset(bangumi.id)

        updated = await db.search_id(bangumi.id)
        assert updated is not None
        assert updated.season_offset == -1
        assert updated.episode_offset == 3

    async def test_nonexistent_bangumi_returns_false(self, db_session):
        db = BangumiDatabase(db_session)
        assert await db.apply_offset(999) is False


def test_groups_are_similar():
    """Test group name similarity detection."""
    from module.database.bangumi import _groups_are_similar

    # Exact match
    assert _groups_are_similar("LoliHouse", "LoliHouse") is True

    # Substring match (one contains the other)
    assert _groups_are_similar("LoliHouse", "LoliHouse&动漫国字幕组") is True
    assert _groups_are_similar("LoliHouse&动漫国字幕组", "LoliHouse") is True

    # Completely different groups
    assert _groups_are_similar("LoliHouse", "Sakurato") is False
    assert _groups_are_similar("字幕组A", "字幕组B") is False

    # Edge cases
    assert _groups_are_similar(None, "LoliHouse") is False
    assert _groups_are_similar("LoliHouse", None) is False
    assert _groups_are_similar(None, None) is False


async def test_get_all_title_patterns(db_session):
    """Test getting all title patterns for a bangumi."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="test",
    )
    await db.add(bangumi)
    bangumi_id = (await db.search_all())[0].id

    # Add aliases
    await db.add_title_alias(bangumi_id, "Test Anime Season 1")
    await db.add_title_alias(bangumi_id, "TA S1")

    # Get all patterns
    updated = await db.search_id(bangumi_id)
    assert updated is not None
    patterns = db.get_all_title_patterns(updated)

    assert len(patterns) == 3
    assert "Test Anime S1" in patterns
    assert "Test Anime Season 1" in patterns
    assert "TA S1" in patterns


async def test_match_list_with_aliases(db_session):
    """Test match_list works with aliases."""
    db = BangumiDatabase(db_session)

    bangumi = Bangumi(
        official_title="Test Anime",
        title_raw="Test Anime S1",
        group_name="TestGroup",
        dpi="1080p",
        source="Web",
        subtitle="CHT",
        rss_link="rss1",
    )
    await db.add(bangumi)
    bangumi_id = (await db.search_all())[0].id
    await db.add_title_alias(bangumi_id, "Test Anime Season 1")

    # Create torrents with different naming patterns
    torrents = [
        Torrent(name="[TestGroup] Test Anime S1 - 01.mkv", url="url1"),
        Torrent(name="[TestGroup] Test Anime Season 1 - 02.mkv", url="url2"),
        Torrent(name="[OtherGroup] Different Anime - 01.mkv", url="url3"),
    ]

    # Only the third torrent should be unmatched
    unmatched = await db.match_list(torrents, "rss2")
    assert len(unmatched) == 1
    assert unmatched[0].name == "[OtherGroup] Different Anime - 01.mkv"


# ============================================================
# RSS Foreign Key Constraint Tests
# ============================================================


class TestRSSDeleteWithTorrents:
    """Regression tests: deleting RSSItem must cascade-delete referencing torrents."""

    async def test_delete_rss_with_torrents(self, db_session):
        """删除 RSSItem 时应自动清除引用它的 torrent 记录。"""
        rss_db = RSSDatabase(db_session)
        torrent_db = TorrentDatabase(db_session)

        # 创建 RSS 和关联的 torrent
        rss = RSSItem(url="https://mikanani.me/RSS/test", name="Test RSS")
        await rss_db.add(rss)

        await torrent_db.add(
            Torrent(name="ep01", url="https://example.com/1", rss_id=rss.id)
        )
        await torrent_db.add(
            Torrent(name="ep02", url="https://example.com/2", rss_id=rss.id)
        )
        # 不关联此 RSS 的 torrent
        await torrent_db.add(
            Torrent(name="other", url="https://example.com/3", rss_id=None)
        )

        assert len(await torrent_db.search_rss(rss.id)) == 2

        # 删除 RSS（不应报外键错误）
        result = await rss_db.delete(rss.id)
        assert result is True

        # RSS 和关联 torrent 都应被删除
        assert await rss_db.search_id(rss.id) is None
        assert len(await torrent_db.search_rss(rss.id)) == 0
        # 无关 torrent 不受影响
        assert len(await torrent_db.search_all()) == 1

    async def test_delete_rss_without_torrents(self, db_session):
        """删除没有关联 torrent 的 RSSItem 应正常工作。"""
        rss_db = RSSDatabase(db_session)

        rss = RSSItem(url="https://mikanani.me/RSS/empty", name="Empty RSS")
        await rss_db.add(rss)

        result = await rss_db.delete(rss.id)
        assert result is True
        assert await rss_db.search_id(rss.id) is None

    async def test_delete_rss_cascades_in_transaction(self, db_session):
        """验证删除操作在同一事务中完成，要么全成功要么全回滚。"""
        rss_db = RSSDatabase(db_session)
        torrent_db = TorrentDatabase(db_session)

        rss = RSSItem(url="https://mikanani.me/RSS/tx", name="TX Test")
        await rss_db.add(rss)

        for i in range(5):
            await torrent_db.add(
                Torrent(
                    name=f"ep{i:02d}", url=f"https://example.com/{i}", rss_id=rss.id
                )
            )

        assert len(await torrent_db.search_rss(rss.id)) == 5

        await rss_db.delete(rss.id)

        # 全部清理干净
        assert await rss_db.search_id(rss.id) is None
        assert len(await torrent_db.search_rss(rss.id)) == 0

    async def test_delete_all_rss_with_torrents(self, db_session):
        """delete_all 应删除所有 RSS 及其关联 torrent。"""
        rss_db = RSSDatabase(db_session)
        torrent_db = TorrentDatabase(db_session)

        rss1 = RSSItem(url="https://mikanani.me/RSS/a", name="RSS A")
        rss2 = RSSItem(url="https://mikanani.me/RSS/b", name="RSS B")
        await rss_db.add(rss1)
        await rss_db.add(rss2)

        await torrent_db.add(
            Torrent(name="t1", url="https://example.com/1", rss_id=rss1.id)
        )
        await torrent_db.add(
            Torrent(name="t2", url="https://example.com/2", rss_id=rss2.id)
        )
        # rss_id 为 None 的 torrent 应不受影响
        await torrent_db.add(
            Torrent(name="orphan", url="https://example.com/3", rss_id=None)
        )

        await rss_db.delete_all()

        assert len(await rss_db.search_all()) == 0
        # 只剩 rss_id 为 None 的
        remaining = await torrent_db.search_all()
        assert len(remaining) == 1
        assert remaining[0].name == "orphan"

    async def test_delete_nonexistent_rss(self, db_session):
        """删除不存在的 RSS 不应报错。"""
        rss_db = RSSDatabase(db_session)
        result = await rss_db.delete(999)
        assert result is True


class TestOrphanTorrents:
    """Tests for TorrentDatabase orphan-torrent operations (bangumi_id IS NULL)."""

    async def test_search_orphans_returns_only_unmatched(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 50)
        await db.add(
            Torrent(name="matched", url="https://example.com/m", bangumi_id=50)
        )
        await db.add(
            Torrent(name="orphan_a", url="https://example.com/a", bangumi_id=None)
        )
        await db.add(
            Torrent(name="orphan_b", url="https://example.com/b", bangumi_id=None)
        )

        orphans = await db.search_orphans()
        assert sorted(t.name for t in orphans) == ["orphan_a", "orphan_b"]

    async def test_count_orphans(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 51)
        await db.add(
            Torrent(name="matched", url="https://example.com/m", bangumi_id=51)
        )
        await db.add(
            Torrent(name="orphan", url="https://example.com/o", bangumi_id=None)
        )

        assert await db.count_orphans() == 1

    async def test_count_orphans_empty(self, db_session):
        db = TorrentDatabase(db_session)
        assert await db.count_orphans() == 0

    async def test_delete_orphans_removes_all_and_returns_count(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 52)
        await db.add(
            Torrent(name="matched", url="https://example.com/m", bangumi_id=52)
        )
        await db.add(
            Torrent(name="orphan_a", url="https://example.com/a", bangumi_id=None)
        )
        await db.add(
            Torrent(name="orphan_b", url="https://example.com/b", bangumi_id=None)
        )

        count = await db.delete_orphans()
        assert count == 2
        remaining = await db.search_all()
        assert len(remaining) == 1
        assert remaining[0].name == "matched"

    async def test_delete_orphans_no_match_returns_zero(self, db_session):
        db = TorrentDatabase(db_session)
        await _ensure_bangumi(db_session, 53)
        await db.add(
            Torrent(name="matched", url="https://example.com/m", bangumi_id=53)
        )

        assert await db.delete_orphans() == 0
        assert len(await db.search_all()) == 1

    async def test_delete_obj_removes_single_torrent(self, db_session):
        db = TorrentDatabase(db_session)
        await db.add(
            Torrent(name="orphan", url="https://example.com/o", bangumi_id=None)
        )
        torrent = (await db.search_all())[0]

        await db.delete_obj(torrent)
        assert await db.search_all() == []

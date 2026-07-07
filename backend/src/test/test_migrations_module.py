"""Tests for the table-driven migration system (module.database.migrations)."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import create_engine

from module.database.migrations import (
    CURRENT_SCHEMA_VERSION,
    MIGRATIONS,
    ensure_schema_version_table,
    get_schema_version,
    run_migrations,
    set_schema_version,
)


def _make_v0_engine():
    """A pre-migration (3.1-era) database: bangumi table without any of the
    migrated columns, no schema_version table.

    title_raw/deleted (bangumi), url (rssitem/torrent), rss_id (torrent) and
    bangumi_id (torrent) are included even though no migration ever ADDs
    them: those columns predate the migration system itself (present since
    the very first schema), unlike the columns below that later migrations
    introduce.
    """
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE bangumi ("
                "  id INTEGER PRIMARY KEY,"
                "  official_title TEXT,"
                "  title_raw TEXT,"
                "  deleted BOOLEAN DEFAULT 0,"
                "  offset INTEGER DEFAULT 0"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE rssitem ("
                "  id INTEGER PRIMARY KEY,"
                "  name TEXT,"
                "  url TEXT"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE torrent ("
                "  id INTEGER PRIMARY KEY,"
                "  name TEXT,"
                "  bangumi_id INTEGER,"
                "  rss_id INTEGER,"
                "  url TEXT"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE user ("
                "  id INTEGER PRIMARY KEY,"
                "  username TEXT,"
                "  password TEXT"
                ")"
            )
        )
    return engine


def _make_versioned_engine(
    version: int,
    *,
    bangumi_extra: str,
    torrent_extra: str = "",
) -> Engine:
    engine = create_engine("sqlite://")
    bangumi_extra_sql = f", {bangumi_extra}" if bangumi_extra else ""
    torrent_extra_sql = f", {torrent_extra}" if torrent_extra else ""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE bangumi ("
                "  id INTEGER PRIMARY KEY,"
                "  official_title TEXT,"
                "  title_raw TEXT,"
                "  deleted BOOLEAN DEFAULT 0,"
                "  air_weekday INTEGER,"
                "  archived BOOLEAN DEFAULT 0"
                f"{bangumi_extra_sql}"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE rssitem ("
                "  id INTEGER PRIMARY KEY,"
                "  name TEXT,"
                "  url TEXT,"
                "  connection_status TEXT,"
                "  last_checked_at TEXT,"
                "  last_error TEXT"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE torrent ("
                "  id INTEGER PRIMARY KEY,"
                "  name TEXT,"
                "  bangumi_id INTEGER,"
                "  rss_id INTEGER,"
                "  url TEXT"
                f"{torrent_extra_sql}"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE user ("
                "  id INTEGER PRIMARY KEY,"
                "  username TEXT,"
                "  password TEXT"
                ")"
            )
        )
        ensure_schema_version_table(conn)
        set_schema_version(conn, version)
    return engine


def _columns(engine, table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


class TestMigrationTable:
    def test_every_migration_has_an_already_applied_guard(self):
        """No migration may rely on the old hardcoded if-ladder."""
        for migration in MIGRATIONS:
            assert callable(
                migration.already_applied
            ), f"migration v{migration.version} has no already_applied guard"

    def test_versions_are_consecutive_from_one(self):
        versions = [m.version for m in MIGRATIONS]
        assert versions == list(range(1, len(MIGRATIONS) + 1))

    def test_current_schema_version_is_derived_from_list(self):
        assert CURRENT_SCHEMA_VERSION == MIGRATIONS[-1].version


class TestRunMigrations:
    def test_upgrades_v0_database_to_current(self):
        engine = _make_v0_engine()
        run_migrations(engine)

        with engine.connect() as conn:
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
        inspector = inspect(engine)
        bangumi_cols = {c["name"] for c in inspector.get_columns("bangumi")}
        assert "air_weekday" in bangumi_cols
        assert "episode_offset" in bangumi_cols
        assert "weekday_locked" in bangumi_cols
        assert "offset" not in bangumi_cols
        assert "passkey" in inspector.get_table_names()

    def test_backfills_indexes_on_upgrading_database(self):
        """v13 must create the title_raw/deleted/archived/url/rss_id indexes
        on a database that predates the SQLModel `index=True` markers --
        those only apply via metadata.create_all on a *fresh* database, so an
        upgrading database would otherwise keep doing full table scans on
        check_new/match_torrent-style lookups forever."""
        engine = _make_v0_engine()
        run_migrations(engine)

        inspector = inspect(engine)
        bangumi_indexes = {ix["name"] for ix in inspector.get_indexes("bangumi")}
        rssitem_indexes = {ix["name"] for ix in inspector.get_indexes("rssitem")}
        torrent_indexes = {ix["name"] for ix in inspector.get_indexes("torrent")}
        assert "ix_bangumi_title_raw" in bangumi_indexes
        assert "ix_bangumi_deleted" in bangumi_indexes
        assert "ix_bangumi_archived" in bangumi_indexes
        assert "ix_rssitem_url" in rssitem_indexes
        assert "ix_torrent_rss_id" in torrent_indexes
        assert "ix_torrent_url" in torrent_indexes

    def test_backfills_torrent_bangumi_id_index(self):
        """v14: search_by_bangumi_id / search_downloaded_by_bangumi_ids
        (offset scanner, RSS preference dedup) filter on torrent.bangumi_id;
        EXPLAIN QUERY PLAN showed a full table scan without this index."""
        engine = _make_v0_engine()
        run_migrations(engine)

        inspector = inspect(engine)
        torrent_indexes = {ix["name"] for ix in inspector.get_indexes("torrent")}
        assert "ix_torrent_bangumi_id" in torrent_indexes

    def test_adds_aria2_renamed_paths_column(self):
        """v15 stores local aria2 file-renames so getFiles can be translated."""
        engine = _make_v0_engine()
        run_migrations(engine)

        inspector = inspect(engine)
        aria2_cols = {c["name"] for c in inspector.get_columns("aria2_gid")}
        assert "renamed_paths" in aria2_cols

    def test_creates_inboxmessage_table(self):
        """v16 creates the in-app notification center table with its indexes."""
        engine = _make_v0_engine()
        run_migrations(engine)

        inspector = inspect(engine)
        assert "inboxmessage" in inspector.get_table_names()
        inbox_indexes = {ix["name"] for ix in inspector.get_indexes("inboxmessage")}
        assert {
            "ix_inboxmessage_kind",
            "ix_inboxmessage_dedup_key",
            "ix_inboxmessage_read",
        } <= inbox_indexes

    def test_creates_llmcredential_table(self):
        """v17 creates the subscription-LLM credential table (unique provider_id)."""
        engine = _make_v0_engine()
        run_migrations(engine)

        inspector = inspect(engine)
        assert "llmcredential" in inspector.get_table_names()
        indexes = {ix["name"]: ix for ix in inspector.get_indexes("llmcredential")}
        assert indexes["ix_llmcredential_provider_id"]["unique"]

    def test_is_idempotent(self):
        engine = _make_v0_engine()
        run_migrations(engine)
        run_migrations(engine)  # must be a no-op, not an error

        with engine.connect() as conn:
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION

    def test_guard_skips_already_applied_migration(self):
        """A column created out-of-band must not make its migration fail."""
        engine = _make_v0_engine()
        with engine.begin() as conn:
            # air_weekday already exists (e.g. created by SQLModel create_all)
            conn.execute(text("ALTER TABLE bangumi ADD COLUMN air_weekday INTEGER"))
        run_migrations(engine)

        with engine.connect() as conn:
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
        inspector = inspect(engine)
        bangumi_cols = {c["name"] for c in inspector.get_columns("bangumi")}
        assert "weekday_locked" in bangumi_cols  # later migrations still ran

    def test_partial_v2_adds_missing_rssitem_connection_columns(self):
        engine = _make_v0_engine()
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE rssitem ADD COLUMN connection_status TEXT"))

        run_migrations(engine)

        rss_cols = _columns(engine, "rssitem")
        assert {"connection_status", "last_checked_at", "last_error"} <= rss_cols

    def test_partial_v5_adds_missing_columns_without_rerunning_rename(self):
        engine = _make_versioned_engine(
            4,
            bangumi_extra="episode_offset INTEGER DEFAULT 0",
        )

        run_migrations(engine)

        bangumi_cols = _columns(engine, "bangumi")
        assert "episode_offset" in bangumi_cols
        assert "season_offset" in bangumi_cols
        assert "needs_review" in bangumi_cols
        assert "needs_review_reason" in bangumi_cols

    def test_partial_v6_adds_missing_qb_hash_index(self):
        engine = _make_versioned_engine(
            5,
            bangumi_extra=(
                "episode_offset INTEGER DEFAULT 0,"
                " season_offset INTEGER DEFAULT 0,"
                " needs_review INTEGER DEFAULT 0,"
                " needs_review_reason TEXT DEFAULT NULL"
            ),
            torrent_extra="qb_hash TEXT",
        )

        run_migrations(engine)

        torrent_indexes = {ix["name"] for ix in inspect(engine).get_indexes("torrent")}
        assert "ix_torrent_qb_hash" in torrent_indexes

    def test_partial_v7_adds_missing_suggested_episode_offset(self):
        engine = _make_versioned_engine(
            6,
            bangumi_extra=(
                "episode_offset INTEGER DEFAULT 0,"
                " season_offset INTEGER DEFAULT 0,"
                " needs_review INTEGER DEFAULT 0,"
                " needs_review_reason TEXT DEFAULT NULL,"
                " suggested_season_offset INTEGER DEFAULT NULL"
            ),
            torrent_extra="qb_hash TEXT",
        )

        run_migrations(engine)

        bangumi_cols = _columns(engine, "bangumi")
        assert "suggested_season_offset" in bangumi_cols
        assert "suggested_episode_offset" in bangumi_cols

    def test_partial_v10_adds_missing_preferred_resolution(self):
        engine = _make_versioned_engine(
            9,
            bangumi_extra=(
                "episode_offset INTEGER DEFAULT 0,"
                " season_offset INTEGER DEFAULT 0,"
                " needs_review INTEGER DEFAULT 0,"
                " needs_review_reason TEXT DEFAULT NULL,"
                " suggested_season_offset INTEGER DEFAULT NULL,"
                " suggested_episode_offset INTEGER DEFAULT NULL,"
                " title_aliases TEXT DEFAULT NULL,"
                " weekday_locked BOOLEAN DEFAULT 0,"
                " preferred_group TEXT DEFAULT NULL"
            ),
            torrent_extra="qb_hash TEXT",
        )

        run_migrations(engine)

        bangumi_cols = _columns(engine, "bangumi")
        assert "preferred_group" in bangumi_cols
        assert "preferred_resolution" in bangumi_cols

    def test_failure_stops_before_bumping_version(self):
        """A failing migration must not record its version as applied.

        run_migrations aborts loudly on failure (so startup aborts too, see
        AppContext.startup) rather than swallowing it -- the caller is
        expected to observe the exception.
        """
        engine = _make_v0_engine()
        with engine.begin() as conn:
            # Sabotage migration 1: its target table is gone, the guard says
            # "not applied", and the ALTER then fails.
            conn.execute(text("DROP TABLE bangumi"))

        with pytest.raises(OperationalError):
            run_migrations(engine)

        with engine.connect() as conn:
            version = get_schema_version(conn)
        # v1 failed immediately: no version may be recorded, later migrations
        # must not have run.
        assert version == 0
        inspector = inspect(engine)
        rssitem_cols = {c["name"] for c in inspector.get_columns("rssitem")}
        assert "connection_status" not in rssitem_cols

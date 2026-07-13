"""Tests for the table-driven migration system (module.database.migrations)."""

from dataclasses import replace

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel import SQLModel, create_engine

import module.database.migrations as migration_module
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


def _make_v19_auth_engine() -> Engine:
    """A real v19 auth schema containing every token field and index."""
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.execute(
            text(
                "CREATE TABLE user ("
                "  id INTEGER PRIMARY KEY,"
                "  username TEXT NOT NULL,"
                "  password TEXT NOT NULL,"
                "  enabled BOOLEAN NOT NULL DEFAULT 1,"
                "  created_at TIMESTAMP NOT NULL,"
                "  updated_at TIMESTAMP NOT NULL"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE auth_session ("
                "  id INTEGER PRIMARY KEY,"
                "  user_id INTEGER NOT NULL REFERENCES user(id),"
                "  token_hash VARCHAR(64) NOT NULL UNIQUE,"
                "  created_at TIMESTAMP NOT NULL,"
                "  last_seen_at TIMESTAMP NOT NULL,"
                "  expires_at TIMESTAMP NOT NULL,"
                "  revoked_at TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE api_token ("
                "  id INTEGER PRIMARY KEY,"
                "  user_id INTEGER NOT NULL REFERENCES user(id),"
                "  name VARCHAR(64) NOT NULL,"
                "  scope VARCHAR(8) NOT NULL,"
                "  token_hash VARCHAR(64) NOT NULL UNIQUE,"
                "  prefix VARCHAR(16) NOT NULL,"
                "  created_at TIMESTAMP NOT NULL,"
                "  last_used_at TIMESTAMP,"
                "  expires_at TIMESTAMP,"
                "  revoked_at TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text("CREATE INDEX ix_auth_session_user_id ON auth_session(user_id)")
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX ix_auth_session_token_hash "
                "ON auth_session(token_hash)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX ix_auth_session_expires_at " "ON auth_session(expires_at)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX ix_auth_session_revoked_at " "ON auth_session(revoked_at)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX ix_api_token_token_hash "
                "ON api_token(token_hash)"
            )
        )
        conn.execute(text("CREATE INDEX ix_api_token_user_id ON api_token(user_id)"))
        conn.execute(text("CREATE INDEX ix_api_token_scope ON api_token(scope)"))
        conn.execute(
            text("CREATE INDEX ix_api_token_expires_at ON api_token(expires_at)")
        )
        conn.execute(
            text("CREATE INDEX ix_api_token_revoked_at ON api_token(revoked_at)")
        )
        conn.execute(
            text(
                "INSERT INTO user "
                "(id, username, password, enabled, created_at, updated_at) VALUES "
                "(7, 'migration_user', 'hashed-password', 1, "
                "'2026-01-01 01:02:03', '2026-01-02 02:03:04')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO api_token "
                "(id, user_id, name, scope, token_hash, prefix, created_at, "
                " last_used_at, expires_at, revoked_at) VALUES "
                "(11, 7, 'active api', 'api', :api_hash, 'tiny', "
                " '2026-02-01 03:04:05', '2026-02-02 04:05:06', "
                " '2027-02-01 03:04:05', NULL),"
                "(12, 7, 'revoked mcp', 'mcp', :mcp_hash, 'legacy-mcp', "
                " '2026-03-01 05:06:07', NULL, NULL, '2026-03-02 06:07:08')"
            ),
            {"api_hash": "a" * 64, "mcp_hash": "b" * 64},
        )
        ensure_schema_version_table(conn)
        set_schema_version(conn, 19)
    return engine


def _columns(engine, table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _run_through_version(
    engine: Engine,
    version: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the real migration table only through one historical version."""
    historical = tuple(item for item in MIGRATIONS if item.version <= version)
    with monkeypatch.context() as patch:
        patch.setattr(migration_module, "MIGRATIONS", historical)
        patch.setattr(migration_module, "CURRENT_SCHEMA_VERSION", version)
        run_migrations(engine)


def _make_v18_movie_engine(monkeypatch: pytest.MonkeyPatch) -> Engine:
    """A database produced by the divergent tokenizer dev branch where v18=Movie."""
    engine = _make_v0_engine()
    _run_through_version(engine, 17, monkeypatch)
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE movie (
                    id INTEGER PRIMARY KEY,
                    official_title VARCHAR NOT NULL,
                    title_raw VARCHAR,
                    year INTEGER,
                    group_name VARCHAR,
                    dpi VARCHAR,
                    source VARCHAR,
                    subtitle VARCHAR,
                    poster_link VARCHAR,
                    rss_link VARCHAR,
                    added BOOLEAN NOT NULL DEFAULT 0,
                    deleted BOOLEAN NOT NULL DEFAULT 0,
                    save_path VARCHAR,
                    rule_name VARCHAR,
                    filter VARCHAR NOT NULL DEFAULT ''
                )"""))
        conn.execute(text("CREATE INDEX ix_movie_title_raw ON movie(title_raw)"))
        conn.execute(text("CREATE INDEX ix_movie_deleted ON movie(deleted)"))
        conn.execute(
            text(
                "INSERT INTO movie "
                "(id, official_title, title_raw, year, filter) VALUES "
                "(9, 'Preserved Movie', 'Preserved Movie', 2026, '')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO user (id, username, password) VALUES "
                "(7, 'movie_dev_user', 'hashed-password')"
            )
        )
        set_schema_version(conn, 18)
    return engine


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
        assert {"enabled", "created_at", "updated_at"} <= _columns(engine, "user")
        assert "auth_session" in inspector.get_table_names()
        assert "api_token" in inspector.get_table_names()
        assert "movie" in inspector.get_table_names()
        user_indexes = {ix["name"] for ix in inspector.get_indexes("user")}
        assert "ix_user_username" in user_indexes

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

    def test_v24_adds_aria2_rename_intent_column(self):
        """v24 persists an ownership proof before moving an aria2 file."""
        engine = _make_v0_engine()
        run_migrations(engine)

        aria2_cols = _columns(engine, "aria2_gid")
        assert "rename_intent" in aria2_cols

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

    def test_v23_creates_durable_rename_operation_schema(self):
        engine = _make_v0_engine()

        run_migrations(engine)

        inspector = inspect(engine)
        assert "rename_operation" in inspector.get_table_names()
        assert {
            "downloader_type",
            "kind",
            "state",
            "new_task_id",
            "old_task_id",
            "save_path",
            "source_path",
            "target_path",
            "staged_path",
            "bangumi_id",
            "media_type",
            "season",
            "episode",
            "group_name",
            "resolution",
            "old_revision",
            "new_revision",
            "revision_metadata",
            "attempt_count",
            "retry_at",
            "notified_at",
            "last_error",
            "created_at",
            "updated_at",
        } <= _columns(engine, "rename_operation")
        indexes = {
            item["name"]: item for item in inspector.get_indexes("rename_operation")
        }
        assert {
            "ux_rename_operation_identity",
            "ux_rename_operation_active_target",
            "ix_rename_operation_state_retry_at",
            "ix_rename_operation_new_task_id",
            "ix_rename_operation_old_task_id",
        } <= set(indexes)
        assert indexes["ux_rename_operation_identity"]["unique"]
        assert indexes["ux_rename_operation_active_target"]["unique"]

    def test_v23_active_target_unique_index_ignores_done_history(self):
        engine = _make_v0_engine()
        run_migrations(engine)
        insert = text(
            "INSERT INTO rename_operation "
            "(downloader_type, kind, state, new_task_id, save_path, "
            " source_path, target_path, attempt_count, created_at, updated_at) "
            "VALUES ('qbittorrent', 'replacement', :state, :task, '/show', "
            " :source, 'Show S01E01.mkv', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        )
        with engine.begin() as conn:
            conn.execute(insert, {"state": "conflict", "task": "v2", "source": "v2"})
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    insert,
                    {"state": "planned", "task": "v3", "source": "v3"},
                )
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE rename_operation SET state = 'done' WHERE new_task_id = 'v2'"
                )
            )
            conn.execute(
                insert,
                {"state": "planned", "task": "v3", "source": "v3"},
            )

    def test_v23_rejects_unknown_operation_state(self):
        engine = _make_v0_engine()
        run_migrations(engine)

        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO rename_operation "
                        "(downloader_type, kind, state, new_task_id, save_path, "
                        " source_path, target_path, attempt_count, created_at, updated_at) "
                        "VALUES ('qbittorrent', 'conflict', 'unknown', 'v2', '/show', "
                        " 'v2.mkv', 'Show S01E01.mkv', 0, CURRENT_TIMESTAMP, "
                        " CURRENT_TIMESTAMP)"
                    )
                )

    def test_v23_guard_accepts_metadata_created_table(self, monkeypatch):
        engine = _make_v0_engine()
        _run_through_version(engine, 22, monkeypatch)
        SQLModel.metadata.create_all(engine)

        run_migrations(engine)

        with engine.connect() as conn:
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
        indexes = {ix["name"] for ix in inspect(engine).get_indexes("rename_operation")}
        assert "ux_rename_operation_active_target" in indexes

    def test_upgrades_auth_beta_v20_without_losing_tokens(self, monkeypatch):
        engine = _make_v19_auth_engine()
        _run_through_version(engine, 20, monkeypatch)
        with engine.connect() as conn:
            before = conn.execute(
                text("SELECT id, token_hash, scope, prefix FROM api_token ORDER BY id")
            ).all()

        run_migrations(engine)

        inspector = inspect(engine)
        assert "movie" in inspector.get_table_names()
        assert {"enabled", "created_at", "updated_at"} <= _columns(engine, "user")
        with engine.connect() as conn:
            after = conn.execute(
                text("SELECT id, token_hash, scope, prefix FROM api_token ORDER BY id")
            ).all()
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
        assert after == before

    def test_repairs_divergent_movie_v18_database(self, monkeypatch):
        engine = _make_v18_movie_engine(monkeypatch)

        run_migrations(engine)

        inspector = inspect(engine)
        assert {"movie", "auth_session", "api_token"} <= set(
            inspector.get_table_names()
        )
        assert {"enabled", "created_at", "updated_at"} <= _columns(engine, "user")
        user_indexes = {index["name"] for index in inspector.get_indexes("user")}
        assert {"ix_user_username", "ix_user_enabled"} <= user_indexes
        token_indexes = {index["name"] for index in inspector.get_indexes("api_token")}
        assert "ix_api_token_token_hash_scope" in token_indexes
        with engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT official_title FROM movie WHERE id = 9")
                ).scalar_one()
                == "Preserved Movie"
            )
            user = conn.execute(
                text(
                    "SELECT username, enabled, created_at, updated_at "
                    "FROM user WHERE id = 7"
                )
            ).one()
            assert user[0] == "movie_dev_user"
            assert user[1] == 1
            assert user[2] is not None
            assert user[3] is not None
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION

    def test_v20_rebuilds_v19_api_tokens_without_losing_data(self):
        engine = _make_v19_auth_engine()
        # Production upgrade paths may call metadata.create_all before the
        # table-driven migrations. It must not disguise a v19 table as v20.
        SQLModel.metadata.create_all(engine)
        assert "ix_api_token_token_hash_scope" not in {
            index["name"] for index in inspect(engine).get_indexes("api_token")
        }
        preserved_fields = (
            "id",
            "user_id",
            "name",
            "scope",
            "token_hash",
            "created_at",
            "last_used_at",
            "expires_at",
            "revoked_at",
        )
        with engine.connect() as conn:
            before = (
                conn.execute(text("SELECT * FROM api_token ORDER BY id"))
                .mappings()
                .all()
            )

        run_migrations(engine)

        with engine.connect() as conn:
            after = (
                conn.execute(text("SELECT * FROM api_token ORDER BY id"))
                .mappings()
                .all()
            )
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION

        assert len(after) == len(before) == 2
        for old, new in zip(before, after):
            assert {field: new[field] for field in preserved_fields} == {
                field: old[field] for field in preserved_fields
            }
            assert new["prefix"] == f"legacy_{new['token_hash'][:8]}"

        inspector = inspect(engine)
        indexes = {index["name"]: index for index in inspector.get_indexes("api_token")}
        composite = indexes["ix_api_token_token_hash_scope"]
        assert composite["unique"]
        assert composite["column_names"] == ["token_hash", "scope"]
        foreign_keys = inspector.get_foreign_keys("api_token")
        assert foreign_keys[0]["referred_table"] == "user"
        assert foreign_keys[0]["constrained_columns"] == ["user_id"]

        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO api_token "
                    "(id, user_id, name, scope, token_hash, prefix, created_at) "
                    "VALUES (13, 7, 'same hash other scope', 'mcp', :token_hash, "
                    "'legacy_aaaaaaaa', '2026-04-01 00:00:00')"
                ),
                {"token_hash": "a" * 64},
            )
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO api_token "
                        "(id, user_id, name, scope, token_hash, prefix, created_at) "
                        "VALUES (14, 7, 'duplicate pair', 'api', :token_hash, "
                        "'legacy_aaaaaaaa', '2026-04-02 00:00:00')"
                    ),
                    {"token_hash": "a" * 64},
                )

    def test_v20_rebuild_rolls_back_if_a_late_statement_fails(self, monkeypatch):
        engine = _make_v19_auth_engine()
        v20 = next(item for item in MIGRATIONS if item.version == 20)
        broken_v20 = replace(
            v20,
            statements=(
                *v20.statements[:3],
                "SELECT * FROM deliberately_missing_v20_table",
                *v20.statements[3:],
            ),
        )
        monkeypatch.setattr(
            migration_module,
            "MIGRATIONS",
            tuple(broken_v20 if item.version == 20 else item for item in MIGRATIONS),
        )

        with pytest.raises(OperationalError):
            run_migrations(engine)

        inspector = inspect(engine)
        assert "api_token" in inspector.get_table_names()
        assert "api_token_v20" not in inspector.get_table_names()
        with engine.connect() as conn:
            assert get_schema_version(conn) == 19
            rows = conn.execute(
                text("SELECT id, prefix FROM api_token ORDER BY id")
            ).all()
        assert rows == [(11, "tiny"), (12, "legacy-mcp")]

    def test_v20_rebuilds_out_of_band_composite_schema_to_redact_prefixes(self):
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO user "
                    "(id, username, password, enabled, created_at, updated_at) VALUES "
                    "(1, 'out_of_band', 'hashed-password', 1, "
                    "'2026-01-01 00:00:00', '2026-01-01 00:00:00')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO api_token "
                    "(id, user_id, name, scope, token_hash, prefix, created_at) VALUES "
                    "(1, 1, 'legacy short token', 'api', :token_hash, 'tiny', "
                    "'2026-01-01 00:00:00')"
                ),
                {"token_hash": "c" * 64},
            )
            ensure_schema_version_table(conn)
            set_schema_version(conn, 19)

        assert "ix_api_token_token_hash_scope" in {
            index["name"] for index in inspect(engine).get_indexes("api_token")
        }
        run_migrations(engine)

        with engine.connect() as conn:
            prefix = conn.execute(
                text("SELECT prefix FROM api_token WHERE id = 1")
            ).scalar_one()
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
        assert prefix == "legacy_cccccccc"

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

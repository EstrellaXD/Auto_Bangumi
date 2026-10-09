"""Tests for database schema migrations (schema_version + guarded DDL)."""

from sqlalchemy import inspect, text
from sqlmodel import Session, create_engine, select

from module.database.combine import CURRENT_SCHEMA_VERSION
from module.database.migrations import (
    create_tables,
    get_schema_version,
    run_migrations,
)
from module.models import Bangumi, RSSItem, Torrent, User


class TestDatabaseMigration:
    """Test that old 3.1.x databases are properly migrated to 3.2.x schema."""

    def _create_old_31x_database(self, engine):
        """Create a database matching the 3.1.x schema (no air_weekday column)."""
        with engine.connect() as conn:
            # Create bangumi table WITHOUT air_weekday (3.1.x schema)
            conn.execute(text("""
                CREATE TABLE bangumi (
                    id INTEGER PRIMARY KEY,
                    official_title TEXT NOT NULL DEFAULT 'official_title',
                    year TEXT,
                    title_raw TEXT NOT NULL DEFAULT 'title_raw',
                    season INTEGER NOT NULL DEFAULT 1,
                    season_raw TEXT,
                    group_name TEXT,
                    dpi TEXT,
                    source TEXT,
                    subtitle TEXT,
                    eps_collect BOOLEAN NOT NULL DEFAULT 0,
                    "offset" INTEGER NOT NULL DEFAULT 0,
                    filter TEXT NOT NULL DEFAULT '720,\\d+-\\d+',
                    rss_link TEXT NOT NULL DEFAULT '',
                    poster_link TEXT,
                    added BOOLEAN NOT NULL DEFAULT 0,
                    rule_name TEXT,
                    save_path TEXT,
                    deleted BOOLEAN NOT NULL DEFAULT 0
                )
            """))
            # Create user table
            conn.execute(text("""
                CREATE TABLE user (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL DEFAULT 'admin',
                    password TEXT NOT NULL DEFAULT 'adminadmin'
                )
            """))
            # Create torrent table
            conn.execute(text("""
                CREATE TABLE torrent (
                    id INTEGER PRIMARY KEY,
                    bangumi_id INTEGER REFERENCES bangumi(id),
                    rss_id INTEGER REFERENCES rssitem(id),
                    name TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT 'https://example.com/torrent',
                    homepage TEXT,
                    downloaded BOOLEAN NOT NULL DEFAULT 0
                )
            """))
            # Create rssitem table
            conn.execute(text("""
                CREATE TABLE rssitem (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    url TEXT NOT NULL DEFAULT 'https://mikanani.me',
                    aggregate BOOLEAN NOT NULL DEFAULT 0,
                    parser TEXT NOT NULL DEFAULT 'mikan',
                    enabled BOOLEAN NOT NULL DEFAULT 1
                )
            """))
            conn.commit()

    def _insert_old_data(self, engine):
        """Insert sample 3.1.x data."""
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO user (username, password) VALUES ('admin', 'adminadmin')
            """))
            conn.execute(text("""
                INSERT INTO bangumi (
                    official_title, year, title_raw, season, group_name,
                    dpi, source, subtitle, eps_collect, "offset",
                    filter, rss_link, poster_link, added, deleted
                ) VALUES (
                    '无职转生', '2021', 'Mushoku Tensei', 1, 'Lilith-Raws',
                    '1080p', 'Baha', 'CHT', 0, 0,
                    '720,\\d+-\\d+', 'https://mikanani.me/RSS/Bangumi?bangumiId=2353',
                    'https://mikanani.me/images/Bangumi/202101/test.jpg', 1, 0
                )
            """))
            conn.execute(text("""
                INSERT INTO bangumi (
                    official_title, year, title_raw, season, group_name,
                    dpi, eps_collect, "offset", filter, rss_link, added, deleted
                ) VALUES (
                    '咒术回战', '2023', 'Jujutsu Kaisen', 2, 'ANi',
                    '1080p', 0, 0, '720', 'https://mikanani.me/RSS/Bangumi?bangumiId=2888',
                    1, 0
                )
            """))
            conn.execute(text("""
                INSERT INTO rssitem (name, url, aggregate, parser, enabled)
                VALUES ('Mikan', 'https://mikanani.me/RSS/MyBangumi?token=abc', 1, 'mikan', 1)
            """))
            conn.execute(text("""
                INSERT INTO torrent (bangumi_id, rss_id, name, url, downloaded)
                VALUES (1, 1, '[Lilith-Raws] Mushoku Tensei - 01.mkv',
                        'https://example.com/torrent1', 1)
            """))
            conn.commit()

    def test_migrate_adds_air_weekday_column(self):
        """Migration should add air_weekday column to bangumi table."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        # Verify air_weekday does NOT exist before migration
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("bangumi")]
        assert "air_weekday" not in columns

        # Run migration
        create_tables(engine)
        run_migrations(engine)

        # Verify air_weekday now exists
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("bangumi")]
        assert "air_weekday" in columns

    def test_migrate_preserves_existing_data(self):
        """Migration should not lose existing bangumi data."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        # Run migration
        create_tables(engine)
        run_migrations(engine)

        # Check data is preserved
        with Session(engine) as s:
            # SQLModel 类属性在 mypy 看来是普通字段类型而非 InstrumentedAttribute
            # （无官方 mypy 插件支持）。
            statement = select(Bangumi).order_by(Bangumi.id)  # type: ignore[arg-type]
            bangumis = list(s.exec(statement).all())
        assert len(bangumis) == 2
        assert bangumis[0].official_title == "无职转生"
        assert bangumis[0].year == "2021"
        assert bangumis[0].season == 1
        assert bangumis[0].group_name == "Lilith-Raws"
        assert bangumis[0].added is True
        assert bangumis[0].air_weekday is None  # New column, should be NULL

        assert bangumis[1].official_title == "咒术回战"
        assert bangumis[1].season == 2

    def test_migrate_preserves_user_data(self):
        """User table should be intact after migration."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        create_tables(engine)
        run_migrations(engine)

        with Session(engine) as s:
            user = s.exec(select(User).where(User.username == "admin")).first()
        assert user is not None
        assert user.username == "admin"

    def test_migrate_preserves_rss_data(self):
        """RSS items should be preserved after migration."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        create_tables(engine)
        run_migrations(engine)

        with Session(engine) as s:
            rss = s.get(RSSItem, 1)
        assert rss is not None
        assert rss.url == "https://mikanani.me/RSS/MyBangumi?token=abc"
        assert rss.aggregate is True

    def test_migrate_preserves_torrent_data(self):
        """Torrent data should be preserved after migration."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        create_tables(engine)
        run_migrations(engine)

        with Session(engine) as s:
            torrent = s.get(Torrent, 1)
        assert torrent is not None
        assert "[Lilith-Raws]" in torrent.name
        assert torrent.downloaded is True

    def test_migrate_idempotent(self):
        """Running migration multiple times should not cause errors."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        # Run migration twice
        create_tables(engine)
        run_migrations(engine)
        run_migrations(engine)  # Should not fail

        with Session(engine) as s:
            bangumis = list(s.exec(select(Bangumi)).all())
        assert len(bangumis) == 2

    def test_new_bangumi_with_air_weekday(self):
        """After migration, new bangumi can be added with air_weekday."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        create_tables(engine)
        run_migrations(engine)

        new_bangumi = Bangumi(
            official_title="葬送的芙莉莲",
            year="2023",
            title_raw="Sousou no Frieren",
            season=1,
            group_name="SubsPlease",
            dpi="1080p",
            rss_link="https://mikanani.me/RSS/test",
            added=True,
            air_weekday=5,  # Friday
        )
        with Session(engine) as s:
            s.add(new_bangumi)
            s.commit()

        with Session(engine) as s:
            result = s.get(Bangumi, 3)
        assert result is not None
        assert result.official_title == "葬送的芙莉莲"
        assert result.air_weekday == 5

    def test_passkey_table_created(self):
        """Migration should create the new passkey table."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        create_tables(engine)
        run_migrations(engine)

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "passkey" in tables

    def test_schema_version_tracked(self):
        """After migration, schema_version table should store current version."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        create_tables(engine)
        run_migrations(engine)

        # Verify schema_version table exists and has correct version
        inspector = inspect(engine)
        assert "schema_version" in inspector.get_table_names()
        with engine.connect() as conn:
            assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION

    def test_schema_version_skips_applied_migrations(self):
        """If schema version is current, run_migrations should be a no-op."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        create_tables(engine)
        run_migrations(engine)

        # Set version to current - second run should skip
        with engine.connect() as conn:
            version_before = get_schema_version(conn)
        run_migrations(engine)
        with engine.connect() as conn:
            version_after = get_schema_version(conn)
        assert version_before == version_after == CURRENT_SCHEMA_VERSION

    def test_schema_version_zero_for_old_db(self):
        """Old database without schema_version table should report version 0."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        with engine.connect() as conn:
            assert get_schema_version(conn) == 0

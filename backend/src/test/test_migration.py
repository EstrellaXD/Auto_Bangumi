"""Tests for config and database migration from 3.1.x to 3.2.x."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from module.conf.config import Settings
from module.database.combine import Database
from module.models import Bangumi, RSSItem, Torrent, User


# --- Mock old 3.1.x config (as stored in config.json) ---
OLD_31X_CONFIG = {
    "program": {
        "sleep_time": 7200,
        "times": 20,
        "webui_port": 7892,
        "data_version": 4.0,
    },
    "downloader": {
        "type": "qbittorrent",
        "host": "192.168.1.100:8080",
        "username": "admin",
        "password": "mypassword",
        "path": "/downloads/Bangumi",
        "ssl": False,
    },
    "rss_parser": {
        "enable": True,
        "type": "mikan",
        "custom_url": "mikanani.me",
        "token": "abc123token",
        "enable_tmdb": True,
        "filter": ["720", "\\d+-\\d+"],
        "language": "zh",
    },
    "bangumi_manage": {
        "enable": True,
        "eps_complete": False,
        "rename_method": "pn",
        "group_tag": True,
        "remove_bad_torrent": False,
    },
    "log": {
        "debug_enable": True,
    },
    "proxy": {
        "enable": True,
        "type": "http",
        "host": "127.0.0.1",
        "port": 7890,
        "username": "",
        "password": "",
    },
    "notification": {
        "enable": True,
        "type": "telegram",
        "token": "bot123456:ABC-DEF",
        "chat_id": "123456789",
    },
}


class TestConfigMigration:
    """Test that old 3.1.x config files are properly migrated."""

    def test_migrate_old_config_renames_program_fields(self):
        """sleep_time -> rss_time, times -> rename_time."""
        result = Settings._migrate_old_config(json.loads(json.dumps(OLD_31X_CONFIG)))
        assert "rss_time" in result["program"]
        assert result["program"]["rss_time"] == 7200
        assert "rename_time" in result["program"]
        assert result["program"]["rename_time"] == 20
        assert "sleep_time" not in result["program"]
        assert "times" not in result["program"]

    def test_migrate_old_config_removes_data_version(self):
        """data_version field should be removed."""
        result = Settings._migrate_old_config(json.loads(json.dumps(OLD_31X_CONFIG)))
        assert "data_version" not in result["program"]

    def test_migrate_old_config_removes_deprecated_rss_fields(self):
        """type, custom_url, token, enable_tmdb should be removed from rss_parser."""
        result = Settings._migrate_old_config(json.loads(json.dumps(OLD_31X_CONFIG)))
        assert "type" not in result["rss_parser"]
        assert "custom_url" not in result["rss_parser"]
        assert "token" not in result["rss_parser"]
        assert "enable_tmdb" not in result["rss_parser"]

    def test_migrate_old_config_preserves_valid_fields(self):
        """Valid fields like rss_parser.filter, downloader.host should be preserved."""
        result = Settings._migrate_old_config(json.loads(json.dumps(OLD_31X_CONFIG)))
        assert result["rss_parser"]["enable"] is True
        assert result["rss_parser"]["filter"] == ["720", "\\d+-\\d+"]
        assert result["rss_parser"]["language"] == "zh"
        assert result["downloader"]["host"] == "192.168.1.100:8080"
        assert result["downloader"]["password"] == "mypassword"
        assert result["notification"]["token"] == "bot123456:ABC-DEF"
        assert result["bangumi_manage"]["group_tag"] is True
        assert result["log"]["debug_enable"] is True
        assert result["proxy"]["port"] == 7890

    def test_migrate_new_config_no_change(self):
        """A config already in 3.2 format should not be altered."""
        new_config = {
            "program": {
                "rss_time": 900,
                "rename_time": 60,
                "webui_port": 7892,
            },
            "rss_parser": {
                "enable": True,
                "filter": ["720"],
                "language": "zh",
            },
        }
        result = Settings._migrate_old_config(json.loads(json.dumps(new_config)))
        assert result["program"]["rss_time"] == 900
        assert result["program"]["rename_time"] == 60

    def test_migrate_does_not_overwrite_new_fields_with_old(self):
        """If both old and new field names exist, keep the new one."""
        config = {
            "program": {
                "sleep_time": 7200,
                "rss_time": 900,
                "times": 20,
                "rename_time": 60,
                "webui_port": 7892,
            },
            "rss_parser": {"enable": True, "filter": [], "language": "zh"},
        }
        result = Settings._migrate_old_config(json.loads(json.dumps(config)))
        assert result["program"]["rss_time"] == 900
        assert result["program"]["rename_time"] == 60
        assert "sleep_time" not in result["program"]
        assert "times" not in result["program"]

    def test_load_old_config_file(self):
        """Full integration: loading a 3.1.x config.json produces correct Settings."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(OLD_31X_CONFIG, f)
            config_path = Path(f.name)

        try:
            with patch("module.conf.config.CONFIG_PATH", config_path):
                settings = Settings()
                # Verify migrated fields
                assert settings.program.rss_time == 7200
                assert settings.program.rename_time == 20
                assert settings.program.webui_port == 7892
                # Verify preserved fields
                assert settings.downloader.host_ == "192.168.1.100:8080"
                assert settings.downloader.password_ == "mypassword"
                assert settings.rss_parser.enable is True
                assert settings.rss_parser.filter == ["720", "\\d+-\\d+"]
                assert settings.notification.enable is True
                assert settings.notification.token_ == "bot123456:ABC-DEF"
                assert settings.bangumi_manage.group_tag is True
                assert settings.log.debug_enable is True
                assert settings.proxy.port == 7890
                # Verify experimental_openai gets defaults
                assert settings.experimental_openai.enable is False
        finally:
            config_path.unlink()

    def test_load_old_config_saves_migrated_format(self):
        """After loading old config, the saved file should use new field names."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(OLD_31X_CONFIG, f)
            config_path = Path(f.name)

        try:
            with patch("module.conf.config.CONFIG_PATH", config_path):
                Settings()
                # Re-read saved config
                with open(config_path) as f:
                    saved = json.load(f)
                assert "rss_time" in saved["program"]
                assert "rename_time" in saved["program"]
                assert "sleep_time" not in saved["program"]
                assert "times" not in saved["program"]
                assert "data_version" not in saved["program"]
                assert "type" not in saved["rss_parser"]
                assert "custom_url" not in saved["rss_parser"]
                assert "token" not in saved["rss_parser"]
                assert "enable_tmdb" not in saved["rss_parser"]
        finally:
            config_path.unlink()


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
        db = Database(engine)
        db.create_table()

        # Verify air_weekday now exists
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("bangumi")]
        assert "air_weekday" in columns

        db.close()

    def test_migrate_preserves_existing_data(self):
        """Migration should not lose existing bangumi data."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        # Run migration
        db = Database(engine)
        db.create_table()

        # Check data is preserved
        bangumis = db.bangumi.search_all()
        assert len(bangumis) == 2
        assert bangumis[0].official_title == "无职转生"
        assert bangumis[0].year == "2021"
        assert bangumis[0].season == 1
        assert bangumis[0].group_name == "Lilith-Raws"
        assert bangumis[0].added is True
        assert bangumis[0].air_weekday is None  # New column, should be NULL

        assert bangumis[1].official_title == "咒术回战"
        assert bangumis[1].season == 2

        db.close()

    def test_migrate_preserves_user_data(self):
        """User table should be intact after migration."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        db = Database(engine)
        db.create_table()

        users = db.user.get_user("admin")
        assert users is not None
        assert users.username == "admin"

        db.close()

    def test_migrate_preserves_rss_data(self):
        """RSS items should be preserved after migration."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        db = Database(engine)
        db.create_table()

        rss = db.rss.search_id(1)
        assert rss is not None
        assert rss.url == "https://mikanani.me/RSS/MyBangumi?token=abc"
        assert rss.aggregate is True

        db.close()

    def test_migrate_preserves_torrent_data(self):
        """Torrent data should be preserved after migration."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        db = Database(engine)
        db.create_table()

        torrent = db.torrent.search(1)
        assert torrent is not None
        assert "[Lilith-Raws]" in torrent.name
        assert torrent.downloaded is True

        db.close()

    def test_migrate_idempotent(self):
        """Running migration multiple times should not cause errors."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        # Run migration twice
        db = Database(engine)
        db.create_table()
        db.create_table()  # Should not fail

        bangumis = db.bangumi.search_all()
        assert len(bangumis) == 2

        db.close()

    def test_new_bangumi_with_air_weekday(self):
        """After migration, new bangumi can be added with air_weekday."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        db = Database(engine)
        db.create_table()

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
        db.bangumi.add(new_bangumi)
        db.commit()

        result = db.bangumi.search_id(3)
        assert result is not None
        assert result.official_title == "葬送的芙莉莲"
        assert result.air_weekday == 5

        db.close()

    def test_passkey_table_created(self):
        """Migration should create the new passkey table."""
        engine = create_engine("sqlite://", echo=False)
        self._create_old_31x_database(engine)
        self._insert_old_data(engine)

        db = Database(engine)
        db.create_table()

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "passkey" in tables

        db.close()

import logging
from typing import Any, get_args, get_origin

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel

from module.models import Bangumi, User
from module.models.passkey import Passkey
from module.models.rss import RSSItem
from module.models.torrent import Torrent

from .bangumi import BangumiDatabase
from .engine import engine as e
from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .user import UserDatabase

logger = logging.getLogger(__name__)

# 所有需要进行空值填充的表模型
TABLE_MODELS: list[type[SQLModel]] = [Bangumi, RSSItem, Torrent, User, Passkey]

# Increment this when adding new migrations to MIGRATIONS list.
CURRENT_SCHEMA_VERSION = 4

# Each migration is a tuple of (version, description, list of SQL statements).
# Migrations are applied in order. A migration at index i brings the schema
# from version i to version i+1.
MIGRATIONS = [
    (
        1,
        "add air_weekday column to bangumi",
        ["ALTER TABLE bangumi ADD COLUMN air_weekday INTEGER"],
    ),
    (
        2,
        "add connection status columns to rssitem",
        [
            "ALTER TABLE rssitem ADD COLUMN connection_status TEXT",
            "ALTER TABLE rssitem ADD COLUMN last_checked_at TEXT",
            "ALTER TABLE rssitem ADD COLUMN last_error TEXT",
        ],
    ),
    (
        3,
        "create passkey table for WebAuthn support",
        [
            """CREATE TABLE IF NOT EXISTS passkey (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES user(id),
                name VARCHAR(64) NOT NULL,
                credential_id VARCHAR NOT NULL UNIQUE,
                public_key VARCHAR NOT NULL,
                sign_count INTEGER DEFAULT 0,
                aaguid VARCHAR,
                transports VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                backup_eligible BOOLEAN DEFAULT 0,
                backup_state BOOLEAN DEFAULT 0
            )""",
            "CREATE INDEX IF NOT EXISTS ix_passkey_user_id ON passkey(user_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_passkey_credential_id ON passkey(credential_id)",
        ],
    ),
    (
        4,
        "add archived column to bangumi",
        ["ALTER TABLE bangumi ADD COLUMN archived BOOLEAN DEFAULT 0"],
    ),
]


class Database(Session):
    def __init__(self, engine=e):
        self.engine = engine
        super().__init__(engine)
        self.rss = RSSDatabase(self)
        self.torrent = TorrentDatabase(self)
        self.bangumi = BangumiDatabase(self)
        self.user = UserDatabase(self)

    def create_table(self):
        SQLModel.metadata.create_all(self.engine)
        self._ensure_schema_version_table()

    def _ensure_schema_version_table(self):
        """Create the schema_version table if it doesn't exist."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS schema_version ("
                    "  id INTEGER PRIMARY KEY,"
                    "  version INTEGER NOT NULL"
                    ")"
                )
            )
            conn.commit()

    def _get_schema_version(self) -> int:
        """Get the current schema version from the database."""
        inspector = inspect(self.engine)
        if "schema_version" not in inspector.get_table_names():
            return 0
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT version FROM schema_version WHERE id = 1")
            )
            row = result.fetchone()
            return row[0] if row else 0

    def _set_schema_version(self, version: int):
        """Update the schema version in the database."""
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, :version)"
                ),
                {"version": version},
            )
            conn.commit()

    def run_migrations(self):
        """Run pending schema migrations based on the stored schema version."""
        self._ensure_schema_version_table()
        current = self._get_schema_version()
        if current >= CURRENT_SCHEMA_VERSION:
            return
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        for version, description, statements in MIGRATIONS:
            if version <= current:
                continue
            # Check if migration is actually needed (column may already exist)
            needs_run = True
            if "bangumi" in tables and version == 1:
                columns = [col["name"] for col in inspector.get_columns("bangumi")]
                if "air_weekday" in columns:
                    needs_run = False
            if "rssitem" in tables and version == 2:
                columns = [col["name"] for col in inspector.get_columns("rssitem")]
                if "connection_status" in columns:
                    needs_run = False
            if version == 3 and "passkey" in tables:
                needs_run = False
            if "bangumi" in tables and version == 4:
                columns = [col["name"] for col in inspector.get_columns("bangumi")]
                if "archived" in columns:
                    needs_run = False
            if needs_run:
                with self.engine.connect() as conn:
                    for stmt in statements:
                        conn.execute(text(stmt))
                    conn.commit()
                logger.info(f"[Database] Migration v{version}: {description}")
            else:
                logger.debug(
                    f"[Database] Migration v{version} skipped (already applied): {description}"
                )
        self._set_schema_version(CURRENT_SCHEMA_VERSION)
        logger.info(f"[Database] Schema version is now {CURRENT_SCHEMA_VERSION}.")
        self._fill_null_with_defaults()

    def _get_field_default(self, field_info: FieldInfo) -> tuple[bool, Any]:
        """
        获取字段的默认值。

        返回:
            (has_default, default_value) - 是否有可用的默认值，以及默认值
        """
        # 跳过 default_factory（如 datetime.utcnow），不适合批量填充
        if field_info.default_factory is not None:
            return False, None
        # 跳过没有默认值的字段（PydanticUndefined）
        if field_info.default is PydanticUndefined:
            return False, None
        return True, field_info.default

    def _is_optional_field(self, model: type[SQLModel], field_name: str) -> bool:
        """检查字段是否为 Optional 类型"""
        hints = model.__annotations__.get(field_name)
        if hints is None:
            return False
        origin = get_origin(hints)
        # Optional[X] 等同于 Union[X, None]
        if origin is not None:
            args = get_args(hints)
            return type(None) in args
        return False

    def _fill_null_with_defaults(self):
        """
        根据模型定义的默认值，自动填充数据库中的 NULL 值。

        规则：
        - 跳过主键字段
        - 跳过 Optional 字段且默认值为 None 的情况
        - 跳过使用 default_factory 的字段
        - 只填充有明确非 None 默认值的字段
        """
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        for model in TABLE_MODELS:
            table_name = model.__tablename__
            if table_name not in tables:
                continue

            db_columns = {col["name"] for col in inspector.get_columns(table_name)}
            fields_to_fill: list[tuple[str, Any]] = []

            for field_name, field_info in model.model_fields.items():
                # 跳过主键
                if field_info.is_required() and field_name == "id":
                    continue
                # 跳过数据库中不存在的列
                if field_name not in db_columns:
                    continue

                has_default, default_value = self._get_field_default(field_info)
                if not has_default:
                    continue
                # 如果是 Optional 且默认值为 None，跳过
                if default_value is None and self._is_optional_field(model, field_name):
                    continue

                fields_to_fill.append((field_name, default_value))

            if not fields_to_fill:
                continue

            with self.engine.connect() as conn:
                for field_name, default_value in fields_to_fill:
                    # 转换 Python 值为 SQL 值
                    if isinstance(default_value, bool):
                        sql_value = 1 if default_value else 0
                    else:
                        sql_value = default_value

                    result = conn.execute(
                        text(
                            f"UPDATE {table_name} SET {field_name} = :val "
                            f"WHERE {field_name} IS NULL"
                        ),
                        {"val": sql_value},
                    )
                    if result.rowcount > 0:
                        logger.info(
                            f"[Database] Filled {result.rowcount} NULL values "
                            f"in {table_name}.{field_name} with default: {default_value}"
                        )
                conn.commit()

    def drop_table(self):
        SQLModel.metadata.drop_all(self.engine)

    def migrate(self):
        # Run migration online
        bangumi_data = self.bangumi.search_all()
        user_data = self.exec("SELECT * FROM user").all()
        readd_bangumi = []
        for bangumi in bangumi_data:
            dict_data = bangumi.dict()
            del dict_data["id"]
            readd_bangumi.append(Bangumi(**dict_data))
        self.drop_table()
        self.create_table()
        self.commit()
        bangumi_data = self.bangumi.search_all()
        self.bangumi.add_all(readd_bangumi)
        self.add(User(**user_data[0]))
        self.commit()

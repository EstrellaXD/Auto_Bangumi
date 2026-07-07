"""表驱动的数据库 schema 迁移。

每个迁移条目自带 ``already_applied`` 守卫，用于判断该迁移是否已被
（例如 ``SQLModel.metadata.create_all``）提前应用，取代旧版
``run_migrations`` 中按版本硬编码的 if 链。

``run_migrations_conn`` 只依赖一个同步 ``Connection``，因此后续可以
直接通过 ``async_engine.begin()`` + ``conn.run_sync(...)`` 执行。
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, get_args, get_origin

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from sqlalchemy import Connection, Engine, inspect, text
from sqlmodel import SQLModel

from module.models import Bangumi, User
from module.models.inbox import InboxMessage
from module.models.llm_credential import LLMCredential
from module.models.passkey import Passkey
from module.models.rss import RSSItem
from module.models.torrent import Torrent

logger = logging.getLogger(__name__)

# 所有需要进行空值填充的表模型
TABLE_MODELS: list[type[SQLModel]] = [
    Bangumi,
    RSSItem,
    Torrent,
    User,
    Passkey,
    InboxMessage,
    LLMCredential,
]

# already_applied 守卫：接收 inspector，返回该迁移是否已生效
AppliedCheck = Callable[[Any], bool]
GuardedStatement = tuple[str, AppliedCheck]


def column_exists(table: str, column: str) -> AppliedCheck:
    def check(inspector) -> bool:
        if table not in inspector.get_table_names():
            return False
        return column in {col["name"] for col in inspector.get_columns(table)}

    return check


def table_exists(table: str) -> AppliedCheck:
    def check(inspector) -> bool:
        return table in inspector.get_table_names()

    return check


def index_exists(table: str, index: str) -> AppliedCheck:
    def check(inspector) -> bool:
        if table not in inspector.get_table_names():
            return False
        return index in {ix["name"] for ix in inspector.get_indexes(table)}

    return check


def all_checks(*checks: AppliedCheck) -> AppliedCheck:
    def check(inspector) -> bool:
        return all(item(inspector) for item in checks)

    return check


@dataclass(frozen=True)
class Migration:
    version: int
    description: str
    statements: tuple[str, ...]
    already_applied: AppliedCheck
    guarded_statements: tuple[GuardedStatement, ...] = ()

    def pending_statements(self, inspector) -> tuple[str, ...]:
        if self.guarded_statements:
            return tuple(
                statement
                for statement, statement_applied in self.guarded_statements
                if not statement_applied(inspector)
            )
        if self.already_applied(inspector):
            return ()
        return self.statements


# 迁移按版本顺序执行；版本号与 3.2.x 的历史保持一致，旧数据库照常升级。
MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        1,
        "add air_weekday column to bangumi",
        ("ALTER TABLE bangumi ADD COLUMN air_weekday INTEGER",),
        column_exists("bangumi", "air_weekday"),
    ),
    Migration(
        2,
        "add connection status columns to rssitem",
        (
            "ALTER TABLE rssitem ADD COLUMN connection_status TEXT",
            "ALTER TABLE rssitem ADD COLUMN last_checked_at TEXT",
            "ALTER TABLE rssitem ADD COLUMN last_error TEXT",
        ),
        all_checks(
            column_exists("rssitem", "connection_status"),
            column_exists("rssitem", "last_checked_at"),
            column_exists("rssitem", "last_error"),
        ),
        (
            (
                "ALTER TABLE rssitem ADD COLUMN connection_status TEXT",
                column_exists("rssitem", "connection_status"),
            ),
            (
                "ALTER TABLE rssitem ADD COLUMN last_checked_at TEXT",
                column_exists("rssitem", "last_checked_at"),
            ),
            (
                "ALTER TABLE rssitem ADD COLUMN last_error TEXT",
                column_exists("rssitem", "last_error"),
            ),
        ),
    ),
    Migration(
        3,
        "create passkey table for WebAuthn support",
        (
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
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_passkey_credential_id "
            "ON passkey(credential_id)",
        ),
        table_exists("passkey"),
    ),
    Migration(
        4,
        "add archived column to bangumi",
        ("ALTER TABLE bangumi ADD COLUMN archived BOOLEAN DEFAULT 0",),
        column_exists("bangumi", "archived"),
    ),
    Migration(
        5,
        "rename offset to episode_offset, add season_offset and review fields",
        (
            "ALTER TABLE bangumi RENAME COLUMN offset TO episode_offset",
            "ALTER TABLE bangumi ADD COLUMN season_offset INTEGER DEFAULT 0",
            "ALTER TABLE bangumi ADD COLUMN needs_review INTEGER DEFAULT 0",
            "ALTER TABLE bangumi ADD COLUMN needs_review_reason TEXT DEFAULT NULL",
        ),
        all_checks(
            column_exists("bangumi", "episode_offset"),
            column_exists("bangumi", "season_offset"),
            column_exists("bangumi", "needs_review"),
            column_exists("bangumi", "needs_review_reason"),
        ),
        (
            (
                "ALTER TABLE bangumi RENAME COLUMN offset TO episode_offset",
                column_exists("bangumi", "episode_offset"),
            ),
            (
                "ALTER TABLE bangumi ADD COLUMN season_offset INTEGER DEFAULT 0",
                column_exists("bangumi", "season_offset"),
            ),
            (
                "ALTER TABLE bangumi ADD COLUMN needs_review INTEGER DEFAULT 0",
                column_exists("bangumi", "needs_review"),
            ),
            (
                "ALTER TABLE bangumi ADD COLUMN needs_review_reason TEXT DEFAULT NULL",
                column_exists("bangumi", "needs_review_reason"),
            ),
        ),
    ),
    Migration(
        6,
        "add qb_hash column to torrent for downloader tracking",
        (
            "ALTER TABLE torrent ADD COLUMN qb_hash TEXT",
            "CREATE INDEX IF NOT EXISTS ix_torrent_qb_hash ON torrent(qb_hash)",
        ),
        all_checks(
            column_exists("torrent", "qb_hash"),
            index_exists("torrent", "ix_torrent_qb_hash"),
        ),
        (
            (
                "ALTER TABLE torrent ADD COLUMN qb_hash TEXT",
                column_exists("torrent", "qb_hash"),
            ),
            (
                "CREATE INDEX IF NOT EXISTS ix_torrent_qb_hash ON torrent(qb_hash)",
                index_exists("torrent", "ix_torrent_qb_hash"),
            ),
        ),
    ),
    Migration(
        7,
        "add suggested offset columns for offset review",
        (
            "ALTER TABLE bangumi ADD COLUMN suggested_season_offset "
            "INTEGER DEFAULT NULL",
            "ALTER TABLE bangumi ADD COLUMN suggested_episode_offset "
            "INTEGER DEFAULT NULL",
        ),
        all_checks(
            column_exists("bangumi", "suggested_season_offset"),
            column_exists("bangumi", "suggested_episode_offset"),
        ),
        (
            (
                "ALTER TABLE bangumi ADD COLUMN suggested_season_offset "
                "INTEGER DEFAULT NULL",
                column_exists("bangumi", "suggested_season_offset"),
            ),
            (
                "ALTER TABLE bangumi ADD COLUMN suggested_episode_offset "
                "INTEGER DEFAULT NULL",
                column_exists("bangumi", "suggested_episode_offset"),
            ),
        ),
    ),
    Migration(
        8,
        "add title_aliases for mid-season naming changes",
        ("ALTER TABLE bangumi ADD COLUMN title_aliases TEXT DEFAULT NULL",),
        column_exists("bangumi", "title_aliases"),
    ),
    Migration(
        9,
        "add weekday_locked column to bangumi",
        ("ALTER TABLE bangumi ADD COLUMN weekday_locked BOOLEAN DEFAULT 0",),
        column_exists("bangumi", "weekday_locked"),
    ),
    Migration(
        10,
        "add preferred_group and preferred_resolution columns to bangumi",
        (
            "ALTER TABLE bangumi ADD COLUMN preferred_group TEXT DEFAULT NULL",
            "ALTER TABLE bangumi ADD COLUMN preferred_resolution TEXT DEFAULT NULL",
        ),
        all_checks(
            column_exists("bangumi", "preferred_group"),
            column_exists("bangumi", "preferred_resolution"),
        ),
        (
            (
                "ALTER TABLE bangumi ADD COLUMN preferred_group TEXT DEFAULT NULL",
                column_exists("bangumi", "preferred_group"),
            ),
            (
                "ALTER TABLE bangumi ADD COLUMN preferred_resolution TEXT DEFAULT NULL",
                column_exists("bangumi", "preferred_resolution"),
            ),
        ),
    ),
    Migration(
        11,
        "create aria2_gid table for aria2 gid<->bangumi association",
        (
            """CREATE TABLE IF NOT EXISTS aria2_gid (
                gid VARCHAR NOT NULL PRIMARY KEY,
                bangumi_id INTEGER REFERENCES bangumi(id),
                category VARCHAR,
                dedup_key VARCHAR,
                created_at TIMESTAMP NOT NULL
            )""",
            "CREATE INDEX IF NOT EXISTS ix_aria2_gid_dedup_key ON aria2_gid(dedup_key)",
        ),
        table_exists("aria2_gid"),
    ),
    Migration(
        12,
        "add episode_type column to bangumi for movie/special support",
        ("ALTER TABLE bangumi ADD COLUMN episode_type TEXT DEFAULT 'episode'",),
        column_exists("bangumi", "episode_type"),
    ),
    Migration(
        13,
        "backfill indexes on bangumi/rssitem/torrent for pre-existing databases "
        "(the SQLModel `index=True` markers only create them via "
        "metadata.create_all on a *fresh* database; upgrading databases never "
        "got them, leaving check_new/match_torrent-style lookups doing full "
        "table scans)",
        (
            "CREATE INDEX IF NOT EXISTS ix_bangumi_title_raw ON bangumi(title_raw)",
            "CREATE INDEX IF NOT EXISTS ix_bangumi_deleted ON bangumi(deleted)",
            "CREATE INDEX IF NOT EXISTS ix_bangumi_archived ON bangumi(archived)",
            "CREATE INDEX IF NOT EXISTS ix_rssitem_url ON rssitem(url)",
            "CREATE INDEX IF NOT EXISTS ix_torrent_rss_id ON torrent(rss_id)",
            "CREATE INDEX IF NOT EXISTS ix_torrent_url ON torrent(url)",
        ),
        lambda inspector: all(
            check(inspector)
            for check in (
                index_exists("bangumi", "ix_bangumi_title_raw"),
                index_exists("bangumi", "ix_bangumi_deleted"),
                index_exists("bangumi", "ix_bangumi_archived"),
                index_exists("rssitem", "ix_rssitem_url"),
                index_exists("torrent", "ix_torrent_rss_id"),
                index_exists("torrent", "ix_torrent_url"),
            )
        ),
    ),
    Migration(
        14,
        "add index on torrent.bangumi_id (EXPLAIN QUERY PLAN showed "
        "search_by_bangumi_id/search_downloaded_by_bangumi_ids doing a full "
        "table scan -- the former runs once per active bangumi on every "
        "offset-scan tick, the latter on every RSS refresh tick when release "
        "preferences are configured)",
        ("CREATE INDEX IF NOT EXISTS ix_torrent_bangumi_id ON torrent(bangumi_id)",),
        index_exists("torrent", "ix_torrent_bangumi_id"),
    ),
    Migration(
        15,
        "add renamed_paths column to aria2_gid for persisted file renames",
        ("ALTER TABLE aria2_gid ADD COLUMN renamed_paths TEXT DEFAULT NULL",),
        column_exists("aria2_gid", "renamed_paths"),
    ),
    Migration(
        16,
        "create inboxmessage table for the in-app notification center",
        (
            """CREATE TABLE IF NOT EXISTS inboxmessage (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL DEFAULT '',
                severity TEXT NOT NULL DEFAULT 'info',
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                payload TEXT,
                dedup_key TEXT,
                read BOOLEAN NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )""",
            "CREATE INDEX IF NOT EXISTS ix_inboxmessage_kind ON inboxmessage(kind)",
            "CREATE INDEX IF NOT EXISTS ix_inboxmessage_dedup_key "
            "ON inboxmessage(dedup_key)",
            "CREATE INDEX IF NOT EXISTS ix_inboxmessage_read ON inboxmessage(read)",
        ),
        table_exists("inboxmessage"),
    ),
    Migration(
        17,
        "create llmcredential table for subscription LLM provider tokens",
        (
            """CREATE TABLE IF NOT EXISTS llmcredential (
                id INTEGER PRIMARY KEY,
                provider_id TEXT NOT NULL DEFAULT '',
                access_token TEXT NOT NULL DEFAULT '',
                refresh_token TEXT NOT NULL DEFAULT '',
                expires_at REAL,
                account_label TEXT NOT NULL DEFAULT '',
                extra TEXT,
                updated_at TEXT NOT NULL DEFAULT ''
            )""",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_llmcredential_provider_id "
            "ON llmcredential(provider_id)",
        ),
        table_exists("llmcredential"),
    ),
)

# 由迁移列表派生，新增迁移时无需手动同步
CURRENT_SCHEMA_VERSION = MIGRATIONS[-1].version


def ensure_schema_version_table(conn: Connection) -> None:
    conn.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "  id INTEGER PRIMARY KEY,"
            "  version INTEGER NOT NULL"
            ")"
        )
    )


def get_schema_version(conn: Connection) -> int:
    if "schema_version" not in inspect(conn).get_table_names():
        return 0
    row = conn.execute(
        text("SELECT version FROM schema_version WHERE id = 1")
    ).fetchone()
    return row[0] if row else 0


def set_schema_version(conn: Connection, version: int) -> None:
    conn.execute(
        text(
            "INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, :version)"
        ),
        {"version": version},
    )


def run_migrations_conn(conn: Connection) -> None:
    """在单个连接上执行所有待应用迁移。

    每个迁移包在 SAVEPOINT 中执行：失败即回滚该迁移并重新抛出异常，使外层
    事务整体回滚、启动失败并高声中止 —— 不允许应用在半迁移的 schema 上继续
    提供服务。
    """
    ensure_schema_version_table(conn)
    current = get_schema_version(conn)
    if current >= CURRENT_SCHEMA_VERSION:
        return
    for migration in MIGRATIONS:
        if migration.version <= current:
            continue
        # 每轮重新 inspect：前一个迁移的 DDL 需要对守卫可见
        pending = migration.pending_statements(inspect(conn))
        if not pending:
            logger.debug(
                f"Migration v{migration.version} skipped "
                f"(already applied): {migration.description}"
            )
        else:
            savepoint = conn.begin_nested()
            try:
                for stmt in pending:
                    conn.execute(text(stmt))
                savepoint.commit()
                logger.info(
                    f"Migration v{migration.version}: " f"{migration.description}"
                )
            except Exception as e:
                savepoint.rollback()
                logger.error(f"Migration v{migration.version} failed: {e}")
                # Abort loudly instead of silently continuing to serve on a
                # half-migrated schema; the outer transaction rolls back.
                raise
        set_schema_version(conn, migration.version)
    logger.info(f"Schema version is now {get_schema_version(conn)}.")
    fill_null_with_defaults_conn(conn)


def run_migrations(engine: Engine) -> None:
    with engine.begin() as conn:
        run_migrations_conn(conn)


def create_tables_conn(conn: Connection) -> None:
    """Sync-Connection body for table creation, usable via ``conn.run_sync``."""
    SQLModel.metadata.create_all(conn)
    ensure_schema_version_table(conn)


def create_tables(engine: Engine) -> None:
    with engine.begin() as conn:
        create_tables_conn(conn)


async def run_migrations_async(async_engine) -> None:
    """Run all pending migrations on the async engine via ``run_sync``."""
    async with async_engine.begin() as conn:
        await conn.run_sync(run_migrations_conn)


async def create_tables_async(async_engine) -> None:
    """Create tables + schema_version on the async engine via ``run_sync``."""
    async with async_engine.begin() as conn:
        await conn.run_sync(create_tables_conn)


def _get_field_default(field_info: FieldInfo) -> tuple[bool, Any]:
    """获取字段的默认值。

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


def _is_optional_field(model: type[SQLModel], field_name: str) -> bool:
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


def fill_null_with_defaults_conn(conn: Connection) -> None:
    """根据模型定义的默认值，自动填充数据库中的 NULL 值。

    规则：
    - 跳过主键字段
    - 跳过 Optional 字段且默认值为 None 的情况
    - 跳过使用 default_factory 的字段
    - 只填充有明确非 None 默认值的字段
    """
    inspector = inspect(conn)
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

            has_default, default_value = _get_field_default(field_info)
            if not has_default:
                continue
            # 如果是 Optional 且默认值为 None，跳过
            if default_value is None and _is_optional_field(model, field_name):
                continue

            fields_to_fill.append((field_name, default_value))

        if not fields_to_fill:
            continue

        for field_name, default_value in fields_to_fill:
            # 转换 Python 值为 SQL 值
            if isinstance(default_value, bool):
                sql_value = 1 if default_value else 0
            else:
                sql_value = default_value

            result = conn.execute(
                text(
                    f'UPDATE "{table_name}" SET "{field_name}" = :val '
                    f'WHERE "{field_name}" IS NULL'
                ),
                {"val": sql_value},
            )
            if result.rowcount > 0:
                logger.info(
                    f"Filled {result.rowcount} NULL values "
                    f"in {table_name}.{field_name} with default: {default_value}"
                )

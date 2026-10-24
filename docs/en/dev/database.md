# Database Developer Guide

This page describes the data layer of the AutoBangumi backend: the engine, the `Database` facade, the repositories, the session rules and the schema migrations. The code is in `backend/src/module/database/`.

## Overview

- The database is the SQLite file `data/data.db`. The ORM is SQLModel (Pydantic + SQLAlchemy).
- The whole application uses only the async engine `sqlite+aiosqlite`. Each connection sets `PRAGMA journal_mode=WAL`, `busy_timeout=5000` and `foreign_keys=ON`. Thus, more than one connection can write at the same time, and a write that collides waits instead of failing at once with `database is locked`.
- Foreign key constraints apply. Before you delete a row that other rows refer to, handle those rows first. For example, `BangumiDatabase.delete_all` deletes the torrent records first.

```
module/database/
├── __init__.py          # Database, get_db (FastAPI dependency)
├── engine.py            # async_engine, async_session_factory, connection PRAGMAs
├── combine.py           # Database: one session plus all repositories
├── migrations.py        # the MIGRATIONS table and the migration runner
├── bangumi.py, rss.py, torrent.py, movie.py, user.py, auth.py,
├── inbox.py, llm_credential.py, rename_operation.py, aria2.py,
└── plugin_kv.py, passkey.py   # one repository for each table
```

## Database and sessions

`Database` is an async context manager. It creates one `AsyncSession` and attaches the repositories to itself. When the `async with` block ends, it closes the session.

```python
from module.database import Database

async with Database() as db:
    rules = await db.bangumi.search_all()
    feeds = await db.rss.search_all()
```

| Attribute | Repository | Table |
| --- | --- | --- |
| `db.bangumi` | `BangumiDatabase` | `bangumi` |
| `db.rss` | `RSSDatabase` | `rssitem` |
| `db.torrent` | `TorrentDatabase` | `torrent` |
| `db.movie` | `MovieDatabase` | `movie` |
| `db.user` | `UserDatabase` | `user` |
| `db.auth` | `AuthDatabase` | `auth_session`, `api_token` |
| `db.inbox` | `InboxDatabase` | notification center |
| `db.llm_credential` | `LLMCredentialDatabase` | LLM subscription credentials |
| `db.rename_operation` | `RenameOperationDatabase` | `rename_operation` (rename conflicts and progress) |
| `db.aria2` | `Aria2GidDatabase` | `aria2_gid` |
| `db.plugin_kv` | `PluginKVDatabase` | `plugin_kv` (the `ctx.kv` of plugins) |

`PasskeyDatabase` is not attached to `Database`. When you need it, make it with `PasskeyDatabase(db.session)`.

`Database` also forwards some session methods: `add` (synchronous, it only queues the object), `commit`, `rollback`, `refresh` and `close`. On SQLite, `begin_write()` runs `BEGIN IMMEDIATE`. Use it when you read and then write and an invariant must stay true. Call it before the first access in the session.

### Session rules

**Use one session for each operation.** Do not keep a session or a `Database` on an object that lives longer than one request or one loop pass. `AppContext` holds no session.

- Routes use dependency injection:

  ```python
  from fastapi import Depends
  from module.database import Database, get_db

  @router.get("/example")
  async def example(db: Database = Depends(get_db)):
      return await db.bangumi.search_all()
  ```

- Scheduled loops and services open their own session for each run: `async with Database() as db:`.
- Services get their dependencies in the constructor: `RSSEngine(db)`, `TorrentManager(db)`. A service uses `self.db.<repository>`. A caller that needs only one repository uses `db.<repository>` directly.
- The session factory sets `expire_on_commit=False`. After a commit, you can still read the attributes of an object, but the object is not attached to a new session. To change it, query it again in the new session.

## Repositories

A repository takes an `AsyncSession`. All of its methods are `async def`, and most of them commit inside the method. When you add a query:

- Put it in the repository of its table. Do not write SQL in a route or a service.
- For many rows, get them in one query with `in_`. Do not query row by row in a loop.
- Soft delete: `bangumi` and `movie` have a `deleted` field. To "disable" a rule, `disable_rule` sets `deleted` to `True`. Only `delete_one` removes the row. When you query active rules, filter on `deleted`.

### More than one downloader

4.0 supports more than one downloader instance (the `plugins.instances` config). `bangumi`, `movie`, `rssitem` and `torrent` all have a `downloader_id` column:

- On rules and feeds, an empty value means "use the default instance" (`plugins.slots.downloader`).
- On a torrent record, it is the instance that has the torrent. Torrents that came from 3.3 have `default`.

## Schema migrations

The migrations are in the `MIGRATIONS` tuple in `migrations.py`. The runner works from this table. The `schema_version` table in the database records the applied version.

```python
Migration(
    26,
    "add downloader_id to bangumi, movie, rssitem and torrent",
    (...SQL statements...),
    already_applied=...,          # guard: is this migration already in effect?
    guarded_statements=(...),     # optional: one guard for each statement
)
```

At startup, AB first runs `SQLModel.metadata.create_all`, then `run_migrations()`:

1. It reads `schema_version` and skips each migration whose version is not larger.
2. For each pending migration, it inspects the database again and calls the guard. If the migration is already in effect (for example, `create_all` made a new database from the models), it only records the version.
3. Otherwise, it runs the statements in one SAVEPOINT. If a statement fails, the migration rolls back and the error goes up. The whole migration transaction rolls back and AB does not start. AB never runs on a schema that is only half migrated.
4. If a migration ran, at the end it fills `NULL` values in existing rows with the model defaults (`fill_null_with_defaults_conn`). It skips primary keys, `default_factory` fields and optional fields whose default is `None`.

### Add a migration

1. Change the model in `module/models/` first. A new database gets the new structure from `create_all`.
2. Append a `Migration` to the end of `MIGRATIONS`. Its version is the previous version plus 1. `CURRENT_SCHEMA_VERSION` comes from the list. Do not edit it manually.
3. Give an `already_applied` guard: `column_exists(table, column)`, `table_exists(table)` or `index_exists(table, index)`. To combine conditions, use `all_checks(...)`. If one migration changes many tables and each table can be in a different state, use `guarded_statements` to give each statement its own guard.
4. Add a test for the migration in `backend/src/test/`: start from the old schema, run the migration and check the result.

```python
Migration(
    27,
    "add note to bangumi",
    ("ALTER TABLE bangumi ADD COLUMN note TEXT DEFAULT ''",),
    column_exists("bangumi", "note"),
)
```

## Tests

`backend/src/test/conftest.py` provides an in-memory database:

- `db_engine`: `sqlite+aiosqlite://` with `StaticPool`. Each test gets a new one, with tables made from the models.
- `db_session`: an `AsyncSession` bound to `db_engine`.

To test a repository directly, use `Database(engine=db_engine)`, or make one repository from `db_session`:

```python
from module.database import Database
from module.database.bangumi import BangumiDatabase
from test.factories import make_bangumi

async def test_add_bangumi(db_engine):
    async with Database(engine=db_engine) as db:
        assert await db.bangumi.add(make_bangumi())

async def test_search(db_session):
    repo = BangumiDatabase(db_session)
    assert await repo.search_all() == []
```

The backend pytest config sets `asyncio_mode = "auto"`, so async test functions need no extra decorator. To run: `cd backend && uv run pytest src/test/test_xxx.py -v`.

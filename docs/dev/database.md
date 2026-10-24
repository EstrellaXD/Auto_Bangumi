# 数据库开发指南

本文说明 AutoBangumi 后端的数据层：引擎、`Database` 门面、仓储、会话约定和 schema 迁移。代码在 `backend/src/module/database/`。

## 概述

- 数据库是 SQLite 文件 `data/data.db`，ORM 是 SQLModel（Pydantic + SQLAlchemy）。
- 整个应用只用异步引擎 `sqlite+aiosqlite`。每个连接设置 `PRAGMA journal_mode=WAL`、`busy_timeout=5000` 和 `foreign_keys=ON`：多个连接可以并发写，冲突的写入会等待而不是立刻报 `database is locked`。
- 外键约束是生效的。删除被引用的行之前，要先处理引用它的行（例如 `BangumiDatabase.delete_all` 先删种子记录）。

```
module/database/
├── __init__.py          # Database、get_db（FastAPI 依赖）
├── engine.py            # async_engine、async_session_factory、连接 PRAGMA
├── combine.py           # Database：一个会话加全部仓储
├── migrations.py        # MIGRATIONS 表与迁移执行
├── bangumi.py、rss.py、torrent.py、movie.py、user.py、auth.py、
├── inbox.py、llm_credential.py、rename_operation.py、aria2.py、
└── plugin_kv.py、passkey.py   # 各表的仓储
```

## Database 与会话

`Database` 是异步上下文管理器。它创建一个 `AsyncSession`，并把仓储挂在自己身上；退出 `async with` 块时关闭会话。

```python
from module.database import Database

async with Database() as db:
    rules = await db.bangumi.search_all()
    feeds = await db.rss.search_all()
```

| 属性 | 仓储 | 表 |
| --- | --- | --- |
| `db.bangumi` | `BangumiDatabase` | `bangumi` |
| `db.rss` | `RSSDatabase` | `rssitem` |
| `db.torrent` | `TorrentDatabase` | `torrent` |
| `db.movie` | `MovieDatabase` | `movie` |
| `db.user` | `UserDatabase` | `user` |
| `db.auth` | `AuthDatabase` | `auth_session`、`api_token` |
| `db.inbox` | `InboxDatabase` | 通知中心 |
| `db.llm_credential` | `LLMCredentialDatabase` | LLM 订阅凭据 |
| `db.rename_operation` | `RenameOperationDatabase` | `rename_operation`（重命名冲突与进度） |
| `db.aria2` | `Aria2GidDatabase` | `aria2_gid` |
| `db.plugin_kv` | `PluginKVDatabase` | `plugin_kv`（插件的 `ctx.kv`） |

`PasskeyDatabase` 不挂在 `Database` 上，需要时用 `PasskeyDatabase(db.session)` 构造。

`Database` 还转发几个会话方法：`add`（同步，只是入队）、`commit`、`rollback`、`refresh`、`close`。`begin_write()` 在 SQLite 上执行 `BEGIN IMMEDIATE`，用于「先读后写且须保持不变量」的场景，必须在本会话的第一次访问之前调用。

### 会话约定

**每次操作一个会话。** 不要把会话或 `Database` 存到比一次请求或一轮循环活得更久的对象上。`AppContext` 不持有会话。

- 路由用依赖注入：

  ```python
  from fastapi import Depends
  from module.database import Database, get_db

  @router.get("/example")
  async def example(db: Database = Depends(get_db)):
      return await db.bangumi.search_all()
  ```

- 定时循环与服务在每次执行时自己开：`async with Database() as db:`。
- 服务在构造函数里接收依赖：`RSSEngine(db)`、`TorrentManager(db)`。服务内部用 `self.db.<仓储>`；只需要一个仓储的调用方直接用 `db.<仓储>`。
- 引擎设置了 `expire_on_commit=False`，提交后对象的属性仍可读，但对象不再与新会话关联。需要修改时，在新的会话里重新查询。

## 仓储

仓储接收一个 `AsyncSession`，方法都是 `async def`，大多在方法内部提交。新增查询时：

- 放进对应表的仓储，不要在路由或服务里直接写 SQL。
- 批量查询用 `in_` 一次取回，不要在循环里逐条查。
- 软删除：`bangumi` 和 `movie` 有 `deleted` 字段。「停用」规则（`disable_rule`）只把 `deleted` 置为 `True`；`delete_one` 才真正删除行。查询活动规则时要过滤 `deleted`。

### 多下载器

4.0 支持多个下载器实例（配置 `plugins.instances`）。`bangumi`、`movie`、`rssitem` 和 `torrent` 都有 `downloader_id` 列：

- 规则与订阅上为空表示「使用默认实例」（`plugins.slots.downloader`）。
- 种子记录上是种子实际所在的实例。从 3.3 升级的存量种子为 `default`。

## Schema 迁移

迁移在 `migrations.py` 的 `MIGRATIONS` 元组中，以表驱动的方式执行。数据库里的 `schema_version` 表记录已应用的版本。

```python
Migration(
    26,
    "add downloader_id to bangumi, movie, rssitem and torrent",
    (...SQL 语句...),
    already_applied=...,          # 守卫：该迁移是否已生效
    guarded_statements=(...),     # 可选：逐条语句的守卫
)
```

启动时 AB 先执行 `SQLModel.metadata.create_all`，再执行 `run_migrations()`：

1. 读取 `schema_version`，跳过版本号不大于它的迁移。
2. 对每个待应用的迁移，重新检查数据库结构，再调用守卫：已生效（例如新库已由 `create_all` 按模型建表）时只记录版本号。
3. 否则在一个 SAVEPOINT 中执行它的语句。任何一条失败，该迁移回滚，异常向上抛出，整个迁移事务回滚，AB 启动失败。AB 不会在只迁移了一半的 schema 上继续运行。
4. 有迁移被执行时，最后按模型的默认值填充存量行中的 `NULL`（`fill_null_with_defaults_conn`）：跳过主键、`default_factory` 字段和默认值为 `None` 的可选字段。

### 添加迁移

1. 先修改 `module/models/` 中的模型。新库由 `create_all` 直接得到新结构。
2. 在 `MIGRATIONS` 末尾追加一个 `Migration`，版本号为上一个加 1。`CURRENT_SCHEMA_VERSION` 由列表推出，不要手动修改。
3. 提供 `already_applied` 守卫：`column_exists(表, 列)`、`table_exists(表)`、`index_exists(表, 索引)`，多个条件用 `all_checks(...)` 组合。一个迁移改多张表、每张表可能处于不同状态时，用 `guarded_statements` 给每条语句单独的守卫。
4. 在 `backend/src/test/` 中为迁移加测试：从旧 schema 开始，执行迁移，检查结果。

```python
Migration(
    27,
    "add note to bangumi",
    ("ALTER TABLE bangumi ADD COLUMN note TEXT DEFAULT ''",),
    column_exists("bangumi", "note"),
)
```

## 测试

`backend/src/test/conftest.py` 提供内存数据库：

- `db_engine`：`sqlite+aiosqlite://` 加 `StaticPool`，每个测试新建并按模型建表。
- `db_session`：绑定 `db_engine` 的 `AsyncSession`。

直接测试仓储时，用 `Database(engine=db_engine)`，或用 `db_session` 构造单个仓储：

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

后端的 pytest 已开启 `asyncio_mode = "auto"`，异步测试函数不需要额外的装饰器。运行：`cd backend && uv run pytest src/test/test_xxx.py -v`。

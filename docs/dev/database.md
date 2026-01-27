# 数据库开发指南

本指南介绍 AutoBangumi 中的数据库架构、模型和操作。

## 概述

AutoBangumi 使用 **SQLite** 作为数据库，使用 **SQLModel**（Pydantic + SQLAlchemy 混合）作为 ORM。数据库文件位于 `data/data.db`。

### 架构

```
module/database/
├── engine.py       # SQLAlchemy 引擎配置
├── combine.py      # Database 类、迁移、会话管理
├── bangumi.py      # 番剧（动画订阅）操作
├── rss.py          # RSS 订阅源操作
├── torrent.py      # 种子跟踪操作
└── user.py         # 用户认证操作
```

## 核心组件

### Database 类

`combine.py` 中的 `Database` 类是主入口点。它继承自 SQLModel 的 `Session`，并提供对所有子数据库的访问：

```python
from module.database import Database

with Database() as db:
    # 访问子数据库
    bangumis = db.bangumi.search_all()
    rss_items = db.rss.search_active()
    torrents = db.torrent.search_all()
```

### 子数据库类

| 类 | 模型 | 用途 |
|-------|-------|---------|
| `BangumiDatabase` | `Bangumi` | 动画订阅规则 |
| `RSSDatabase` | `RSSItem` | RSS 订阅源 |
| `TorrentDatabase` | `Torrent` | 已下载种子跟踪 |
| `UserDatabase` | `User` | 认证 |

## 模型

### Bangumi 模型

动画订阅的核心模型：

```python
class Bangumi(SQLModel, table=True):
    id: int                          # 主键
    official_title: str              # 显示名称（如"无职转生"）
    title_raw: str                   # 用于种子匹配的原始标题（有索引）
    season: int = 1                  # 季度编号
    episode_offset: int = 0          # 集数编号调整
    season_offset: int = 0           # 季度编号调整
    rss_link: str                    # 逗号分隔的 RSS 订阅源 URL
    filter: str                      # 排除过滤器（如 "720,\\d+-\\d+"）
    poster_link: str                 # TMDB 海报 URL
    save_path: str                   # 下载目标路径
    rule_name: str                   # qBittorrent RSS 规则名称
    added: bool = False              # 规则是否已添加到下载器
    deleted: bool = False            # 软删除标志（有索引）
    archived: bool = False           # 用于已完结系列（有索引）
    needs_review: bool = False       # 检测到偏移不匹配
    needs_review_reason: str         # 需要审核的原因
    suggested_season_offset: int     # 建议的季度偏移
    suggested_episode_offset: int    # 建议的集数偏移
    air_weekday: int                 # 放送日（0=周日，6=周六）
```

### RSSItem 模型

RSS 订阅源：

```python
class RSSItem(SQLModel, table=True):
    id: int                          # 主键
    name: str                        # 显示名称
    url: str                         # 订阅源 URL（唯一，有索引）
    aggregate: bool = True           # 是否解析种子
    parser: str = "mikan"            # 解析器类型：mikan、dmhy、nyaa
    enabled: bool = True             # 启用标志
    connection_status: str           # "healthy" 或 "error"
    last_checked_at: str             # ISO 时间戳
    last_error: str                  # 最后一次错误消息
```

### Torrent 模型

跟踪已下载的种子：

```python
class Torrent(SQLModel, table=True):
    id: int                          # 主键
    name: str                        # 种子名称（有索引）
    url: str                         # 种子/磁力链接 URL（唯一，有索引）
    rss_id: int                      # 来源 RSS 订阅源 ID
    bangumi_id: int                  # 关联的番剧 ID（可为空）
    qb_hash: str                     # qBittorrent 信息哈希（有索引）
    downloaded: bool = False         # 下载完成
```

## 常用操作

### BangumiDatabase

```python
with Database() as db:
    # 创建
    db.bangumi.add(bangumi)              # 单条插入
    db.bangumi.add_all(bangumi_list)     # 批量插入（去重）

    # 读取
    db.bangumi.search_all()              # 所有记录（缓存，5分钟 TTL）
    db.bangumi.search_id(123)            # 按 ID 查询
    db.bangumi.match_torrent("torrent name")  # 按 title_raw 匹配查找
    db.bangumi.not_complete()            # 未完结系列
    db.bangumi.get_needs_review()        # 标记需要审核的

    # 更新
    db.bangumi.update(bangumi)           # 更新单条记录
    db.bangumi.update_all(bangumi_list)  # 批量更新

    # 删除
    db.bangumi.delete_one(123)           # 硬删除
    db.bangumi.disable_rule(123)         # 软删除（deleted=True）
```

### RSSDatabase

```python
with Database() as db:
    # 创建
    db.rss.add(rss_item)                 # 单条插入
    db.rss.add_all(rss_items)            # 批量插入（去重）

    # 读取
    db.rss.search_all()                  # 所有订阅源
    db.rss.search_active()               # 仅启用的订阅源
    db.rss.search_aggregate()            # 启用且 aggregate=True

    # 更新
    db.rss.update(id, rss_update)        # 部分更新
    db.rss.enable(id)                    # 启用订阅源
    db.rss.disable(id)                   # 禁用订阅源
    db.rss.enable_batch([1, 2, 3])       # 批量启用
    db.rss.disable_batch([1, 2, 3])      # 批量禁用
```

### TorrentDatabase

```python
with Database() as db:
    # 创建
    db.torrent.add(torrent)              # 单条插入
    db.torrent.add_all(torrents)         # 批量插入

    # 读取
    db.torrent.search_all()              # 所有种子
    db.torrent.search_by_qb_hash(hash)   # 按 qBittorrent 哈希查询
    db.torrent.search_by_url(url)        # 按 URL 查询
    db.torrent.check_new(torrents)       # 过滤掉已存在的

    # 更新
    db.torrent.update_qb_hash(id, hash)  # 设置 qb_hash
```

## 缓存

### 番剧缓存

`search_all()` 的结果在模块级别缓存，TTL 为 5 分钟：

```python
# bangumi.py 中的模块级缓存
_bangumi_cache: list[Bangumi] | None = None
_bangumi_cache_time: float = 0
_BANGUMI_CACHE_TTL: float = 300.0  # 5 分钟

# 缓存失效
def _invalidate_bangumi_cache():
    global _bangumi_cache, _bangumi_cache_time
    _bangumi_cache = None
    _bangumi_cache_time = 0
```

**重要：** 缓存在以下操作时自动失效：
- `add()`、`add_all()`
- `update()`、`update_all()`
- `delete_one()`、`delete_all()`
- `archive_one()`、`unarchive_one()`
- 任何 RSS 链接更新操作

### 会话分离

缓存的对象会从会话中**分离**，以防止 `DetachedInstanceError`：

```python
for b in bangumis:
    self.session.expunge(b)  # 从会话中分离
```

## 迁移系统

### Schema 版本控制

迁移通过 `schema_version` 表跟踪：

```python
CURRENT_SCHEMA_VERSION = 7

# 每个迁移：(版本号, 描述, [SQL 语句])
MIGRATIONS = [
    (1, "add air_weekday column", [...]),
    (2, "add connection status columns", [...]),
    (3, "create passkey table", [...]),
    (4, "add archived column", [...]),
    (5, "rename offset to episode_offset", [...]),
    (6, "add qb_hash column", [...]),
    (7, "add suggested offset columns", [...]),
]
```

### 添加新迁移

1. 在 `combine.py` 中增加 `CURRENT_SCHEMA_VERSION`
2. 在 `MIGRATIONS` 列表中添加迁移元组：

```python
MIGRATIONS = [
    # ... 现有迁移 ...
    (
        8,
        "add my_new_column to bangumi",
        [
            "ALTER TABLE bangumi ADD COLUMN my_new_column TEXT DEFAULT NULL",
        ],
    ),
]
```

3. 在 `run_migrations()` 中添加幂等性检查：

```python
if "bangumi" in tables and version == 8:
    columns = [col["name"] for col in inspector.get_columns("bangumi")]
    if "my_new_column" in columns:
        needs_run = False
```

4. 更新 `module/models/` 中对应的 Pydantic 模型

### 默认值回填

迁移后，`_fill_null_with_defaults()` 会根据模型默认值自动填充 NULL 值：

```python
# 如果模型定义为：
class Bangumi(SQLModel, table=True):
    my_field: bool = False

# 那么现有记录中的 NULL 值将被更新为 False
```

## 性能模式

### 批量查询

`add_all()` 使用单个查询检查重复项，而不是 N 个查询：

```python
# 高效：单个 SELECT
keys_to_check = [(d.title_raw, d.group_name) for d in datas]
conditions = [
    and_(Bangumi.title_raw == tr, Bangumi.group_name == gn)
    for tr, gn in keys_to_check
]
statement = select(Bangumi.title_raw, Bangumi.group_name).where(or_(*conditions))
```

### 正则表达式匹配

`match_list()` 为所有标题匹配编译单个正则表达式模式：

```python
# 编译一次，匹配多次
sorted_titles = sorted(title_index.keys(), key=len, reverse=True)
pattern = "|".join(re.escape(title) for title in sorted_titles)
title_regex = re.compile(pattern)

# 每个种子 O(1) 查找而不是 O(n)
for torrent in torrent_list:
    match = title_regex.search(torrent.name)
```

### 索引列

以下列具有索引以实现快速查找：

| 表 | 列 | 索引类型 |
|-------|--------|------------|
| `bangumi` | `title_raw` | 普通 |
| `bangumi` | `deleted` | 普通 |
| `bangumi` | `archived` | 普通 |
| `rssitem` | `url` | 唯一 |
| `torrent` | `name` | 普通 |
| `torrent` | `url` | 唯一 |
| `torrent` | `qb_hash` | 普通 |

## 测试

### 测试数据库设置

测试使用内存中的 SQLite 数据库：

```python
# conftest.py
@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session
```

### 工厂函数

使用工厂函数创建测试数据：

```python
from test.factories import make_bangumi, make_torrent, make_rss_item

def test_bangumi_search():
    bangumi = make_bangumi(title_raw="Test Title", season=2)
    # ... 测试逻辑
```

## 设计说明

### 无外键

SQLite 外键强制默认是禁用的。关系（如 `Torrent.bangumi_id`）在应用程序逻辑中管理，而不是通过数据库约束。

### 软删除

`Bangumi.deleted` 标志启用软删除。面向用户的数据查询应按 `deleted=False` 过滤：

```python
statement = select(Bangumi).where(Bangumi.deleted == false())
```

### 种子标记

种子在 qBittorrent 中使用 `ab:{bangumi_id}` 标记，用于重命名操作时的偏移查找。这使得无需数据库查询即可快速识别番剧。

## 常见问题

### DetachedInstanceError

如果您从不同的会话访问缓存的对象：

```python
# 错误：在新会话中访问缓存的对象
bangumis = db.bangumi.search_all()  # 已缓存
with Database() as new_db:
    new_db.session.add(bangumis[0])  # 错误！

# 正确：对象已分离，可独立工作
bangumis = db.bangumi.search_all()
bangumis[0].title_raw = "New Title"  # 可以，但不会持久化
```

### 缓存过期

如果手动 SQL 更新绕过了 ORM，请使缓存失效：

```python
from module.database.bangumi import _invalidate_bangumi_cache

with engine.connect() as conn:
    conn.execute(text("UPDATE bangumi SET ..."))
    conn.commit()

_invalidate_bangumi_cache()  # 重要！
```

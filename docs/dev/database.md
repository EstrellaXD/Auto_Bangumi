# Database Developer Guide

This guide covers the database architecture, models, and operations in AutoBangumi.

## Overview

AutoBangumi uses **SQLite** as its database with **SQLModel** (Pydantic + SQLAlchemy hybrid) for ORM. The database file is located at `data/data.db`.

### Architecture

```
module/database/
├── engine.py       # SQLAlchemy engine configuration
├── combine.py      # Database class, migrations, session management
├── bangumi.py      # Bangumi (anime subscription) operations
├── rss.py          # RSS feed operations
├── torrent.py      # Torrent tracking operations
└── user.py         # User authentication operations
```

## Core Components

### Database Class

The `Database` class in `combine.py` is the main entry point. It inherits from SQLModel's `Session` and provides access to all sub-databases:

```python
from module.database import Database

with Database() as db:
    # Access sub-databases
    bangumis = db.bangumi.search_all()
    rss_items = db.rss.search_active()
    torrents = db.torrent.search_all()
```

### Sub-Database Classes

| Class | Model | Purpose |
|-------|-------|---------|
| `BangumiDatabase` | `Bangumi` | Anime subscription rules |
| `RSSDatabase` | `RSSItem` | RSS feed sources |
| `TorrentDatabase` | `Torrent` | Downloaded torrent tracking |
| `UserDatabase` | `User` | Authentication |

## Models

### Bangumi Model

Core model for anime subscriptions:

```python
class Bangumi(SQLModel, table=True):
    id: int                          # Primary key
    official_title: str              # Display name (e.g., "Mushoku Tensei")
    title_raw: str                   # Raw title for torrent matching (indexed)
    season: int = 1                  # Season number
    episode_offset: int = 0          # Episode numbering adjustment
    season_offset: int = 0           # Season numbering adjustment
    rss_link: str                    # Comma-separated RSS feed URLs
    filter: str                      # Exclusion filter (e.g., "720,\\d+-\\d+")
    poster_link: str                 # TMDB poster URL
    save_path: str                   # Download destination path
    rule_name: str                   # qBittorrent RSS rule name
    added: bool = False              # Whether rule is added to downloader
    deleted: bool = False            # Soft delete flag (indexed)
    archived: bool = False           # For completed series (indexed)
    needs_review: bool = False       # Offset mismatch detected
    needs_review_reason: str         # Reason for review
    suggested_season_offset: int     # Suggested season offset
    suggested_episode_offset: int    # Suggested episode offset
    air_weekday: int                 # Airing day (0=Sunday, 6=Saturday)
```

### RSSItem Model

RSS feed subscriptions:

```python
class RSSItem(SQLModel, table=True):
    id: int                          # Primary key
    name: str                        # Display name
    url: str                         # Feed URL (unique, indexed)
    aggregate: bool = True           # Whether to parse torrents
    parser: str = "mikan"            # Parser type: mikan, dmhy, nyaa
    enabled: bool = True             # Active flag
    connection_status: str           # "healthy" or "error"
    last_checked_at: str             # ISO timestamp
    last_error: str                  # Last error message
```

### Torrent Model

Tracks downloaded torrents:

```python
class Torrent(SQLModel, table=True):
    id: int                          # Primary key
    name: str                        # Torrent name (indexed)
    url: str                         # Torrent/magnet URL (unique, indexed)
    rss_id: int                      # Source RSS feed ID
    bangumi_id: int                  # Linked Bangumi ID (nullable)
    qb_hash: str                     # qBittorrent info hash (indexed)
    downloaded: bool = False         # Download completed
```

## Common Operations

### BangumiDatabase

```python
with Database() as db:
    # Create
    db.bangumi.add(bangumi)              # Single insert
    db.bangumi.add_all(bangumi_list)     # Batch insert (deduplicates)

    # Read
    db.bangumi.search_all()              # All records (cached, 5min TTL)
    db.bangumi.search_id(123)            # By ID
    db.bangumi.match_torrent("torrent name")  # Find by title_raw match
    db.bangumi.not_complete()            # Incomplete series
    db.bangumi.get_needs_review()        # Flagged for review

    # Update
    db.bangumi.update(bangumi)           # Update single record
    db.bangumi.update_all(bangumi_list)  # Batch update

    # Delete
    db.bangumi.delete_one(123)           # Hard delete
    db.bangumi.disable_rule(123)         # Soft delete (deleted=True)
```

### RSSDatabase

```python
with Database() as db:
    # Create
    db.rss.add(rss_item)                 # Single insert
    db.rss.add_all(rss_items)            # Batch insert (deduplicates)

    # Read
    db.rss.search_all()                  # All feeds
    db.rss.search_active()               # Enabled feeds only
    db.rss.search_aggregate()            # Enabled + aggregate=True

    # Update
    db.rss.update(id, rss_update)        # Partial update
    db.rss.enable(id)                    # Enable feed
    db.rss.disable(id)                   # Disable feed
    db.rss.enable_batch([1, 2, 3])       # Batch enable
    db.rss.disable_batch([1, 2, 3])      # Batch disable
```

### TorrentDatabase

```python
with Database() as db:
    # Create
    db.torrent.add(torrent)              # Single insert
    db.torrent.add_all(torrents)         # Batch insert

    # Read
    db.torrent.search_all()              # All torrents
    db.torrent.search_by_qb_hash(hash)   # By qBittorrent hash
    db.torrent.search_by_url(url)        # By URL
    db.torrent.check_new(torrents)       # Filter out existing

    # Update
    db.torrent.update_qb_hash(id, hash)  # Set qb_hash
```

## Caching

### Bangumi Cache

`search_all()` results are cached at the module level with a 5-minute TTL:

```python
# Module-level cache in bangumi.py
_bangumi_cache: list[Bangumi] | None = None
_bangumi_cache_time: float = 0
_BANGUMI_CACHE_TTL: float = 300.0  # 5 minutes

# Cache invalidation
def _invalidate_bangumi_cache():
    global _bangumi_cache, _bangumi_cache_time
    _bangumi_cache = None
    _bangumi_cache_time = 0
```

**Important:** The cache is automatically invalidated on:
- `add()`, `add_all()`
- `update()`, `update_all()`
- `delete_one()`, `delete_all()`
- `archive_one()`, `unarchive_one()`
- Any RSS link update operations

### Session Expunge

Cached objects are **expunged** from the session to prevent `DetachedInstanceError`:

```python
for b in bangumis:
    self.session.expunge(b)  # Detach from session
```

## Migration System

### Schema Versioning

Migrations are tracked via a `schema_version` table:

```python
CURRENT_SCHEMA_VERSION = 7

# Each migration: (version, description, [SQL statements])
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

### Adding a New Migration

1. Increment `CURRENT_SCHEMA_VERSION` in `combine.py`
2. Add migration tuple to `MIGRATIONS` list:

```python
MIGRATIONS = [
    # ... existing migrations ...
    (
        8,
        "add my_new_column to bangumi",
        [
            "ALTER TABLE bangumi ADD COLUMN my_new_column TEXT DEFAULT NULL",
        ],
    ),
]
```

3. Add idempotency check in `run_migrations()`:

```python
if "bangumi" in tables and version == 8:
    columns = [col["name"] for col in inspector.get_columns("bangumi")]
    if "my_new_column" in columns:
        needs_run = False
```

4. Update the corresponding Pydantic model in `module/models/`

### Default Value Backfill

After migrations, `_fill_null_with_defaults()` automatically fills NULL values based on model defaults:

```python
# If model defines:
class Bangumi(SQLModel, table=True):
    my_field: bool = False

# Then existing rows with NULL will be updated to False
```

## Performance Patterns

### Batch Queries

`add_all()` uses a single query to check for duplicates instead of N queries:

```python
# Efficient: single SELECT
keys_to_check = [(d.title_raw, d.group_name) for d in datas]
conditions = [
    and_(Bangumi.title_raw == tr, Bangumi.group_name == gn)
    for tr, gn in keys_to_check
]
statement = select(Bangumi.title_raw, Bangumi.group_name).where(or_(*conditions))
```

### Regex Matching

`match_list()` compiles a single regex pattern for all title matches:

```python
# Compile once, match many
sorted_titles = sorted(title_index.keys(), key=len, reverse=True)
pattern = "|".join(re.escape(title) for title in sorted_titles)
title_regex = re.compile(pattern)

# O(1) lookup per torrent instead of O(n)
for torrent in torrent_list:
    match = title_regex.search(torrent.name)
```

### Indexed Columns

The following columns have indexes for fast lookups:

| Table | Column | Index Type |
|-------|--------|------------|
| `bangumi` | `title_raw` | Regular |
| `bangumi` | `deleted` | Regular |
| `bangumi` | `archived` | Regular |
| `rssitem` | `url` | Unique |
| `torrent` | `name` | Regular |
| `torrent` | `url` | Unique |
| `torrent` | `qb_hash` | Regular |

## Testing

### Test Database Setup

Tests use an in-memory SQLite database:

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

### Factory Functions

Use factory functions for creating test data:

```python
from test.factories import make_bangumi, make_torrent, make_rss_item

def test_bangumi_search():
    bangumi = make_bangumi(title_raw="Test Title", season=2)
    # ... test logic
```

## Design Notes

### No Foreign Keys

SQLite foreign key enforcement is disabled by default. Relationships (like `Torrent.bangumi_id`) are managed in application logic rather than database constraints.

### Soft Deletes

The `Bangumi.deleted` flag enables soft deletes. Queries should filter by `deleted=False` for user-facing data:

```python
statement = select(Bangumi).where(Bangumi.deleted == false())
```

### Torrent Tagging

Torrents are tagged in qBittorrent with `ab:{bangumi_id}` for offset lookup during rename operations. This enables fast bangumi identification without database queries.

## Common Issues

### DetachedInstanceError

If you access cached objects from a different session:

```python
# Wrong: accessing cached object in new session
bangumis = db.bangumi.search_all()  # Cached
with Database() as new_db:
    new_db.session.add(bangumis[0])  # Error!

# Right: objects are expunged, work independently
bangumis = db.bangumi.search_all()
bangumis[0].title_raw = "New Title"  # OK, but won't persist
```

### Cache Staleness

If manual SQL updates bypass the ORM, invalidate the cache:

```python
from module.database.bangumi import _invalidate_bangumi_cache

with engine.connect() as conn:
    conn.execute(text("UPDATE bangumi SET ..."))
    conn.commit()

_invalidate_bangumi_cache()  # Important!
```

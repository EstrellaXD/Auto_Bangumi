# データベース開発者ガイド

このガイドでは、AutoBangumiのデータベースアーキテクチャ、モデル、および操作について説明します。

## 概要

AutoBangumiはデータベースとして**SQLite**を使用し、ORMには**SQLModel**（Pydantic + SQLAlchemyハイブリッド）を使用しています。データベースファイルは`data/data.db`にあります。

### アーキテクチャ

```
module/database/
├── engine.py       # SQLAlchemyエンジン設定
├── combine.py      # Databaseクラス、マイグレーション、セッション管理
├── bangumi.py      # Bangumi（アニメ購読）操作
├── rss.py          # RSSフィード操作
├── torrent.py      # トレント追跡操作
└── user.py         # ユーザー認証操作
```

## コアコンポーネント

### Databaseクラス

`combine.py`の`Database`クラスがメインエントリーポイントです。SQLModelの`Session`を継承し、すべてのサブデータベースへのアクセスを提供します：

```python
from module.database import Database

with Database() as db:
    # サブデータベースへのアクセス
    bangumis = db.bangumi.search_all()
    rss_items = db.rss.search_active()
    torrents = db.torrent.search_all()
```

### サブデータベースクラス

| クラス | モデル | 目的 |
|-------|-------|------|
| `BangumiDatabase` | `Bangumi` | アニメ購読ルール |
| `RSSDatabase` | `RSSItem` | RSSフィードソース |
| `TorrentDatabase` | `Torrent` | ダウンロードしたトレントの追跡 |
| `UserDatabase` | `User` | 認証 |

## モデル

### Bangumiモデル

アニメ購読のコアモデル：

```python
class Bangumi(SQLModel, table=True):
    id: int                          # 主キー
    official_title: str              # 表示名（例："無職転生"）
    title_raw: str                   # トレントマッチング用の生タイトル（インデックス付き）
    season: int = 1                  # シーズン番号
    episode_offset: int = 0          # エピソード番号調整
    season_offset: int = 0           # シーズン番号調整
    rss_link: str                    # カンマ区切りRSSフィードURL
    filter: str                      # 除外フィルター（例："720,\\d+-\\d+"）
    poster_link: str                 # TMDBポスターURL
    save_path: str                   # ダウンロード先パス
    rule_name: str                   # qBittorrent RSSルール名
    added: bool = False              # ルールがダウンローダーに追加されたかどうか
    deleted: bool = False            # ソフト削除フラグ（インデックス付き）
    archived: bool = False           # 完結シリーズ用（インデックス付き）
    needs_review: bool = False       # オフセット不一致検出
    needs_review_reason: str         # レビューの理由
    suggested_season_offset: int     # 提案されたシーズンオフセット
    suggested_episode_offset: int    # 提案されたエピソードオフセット
    air_weekday: int                 # 放送日（0=日曜日、6=土曜日）
```

### RSSItemモデル

RSSフィード購読：

```python
class RSSItem(SQLModel, table=True):
    id: int                          # 主キー
    name: str                        # 表示名
    url: str                         # フィードURL（ユニーク、インデックス付き）
    aggregate: bool = True           # トレントを解析するかどうか
    parser: str = "mikan"            # パーサータイプ：mikan、dmhy、nyaa
    enabled: bool = True             # アクティブフラグ
    connection_status: str           # "healthy"または"error"
    last_checked_at: str             # ISOタイムスタンプ
    last_error: str                  # 最後のエラーメッセージ
```

### Torrentモデル

ダウンロードしたトレントを追跡：

```python
class Torrent(SQLModel, table=True):
    id: int                          # 主キー
    name: str                        # トレント名（インデックス付き）
    url: str                         # トレント/マグネットURL（ユニーク、インデックス付き）
    rss_id: int                      # ソースRSSフィードID
    bangumi_id: int                  # リンクされたBangumi ID（nullable）
    qb_hash: str                     # qBittorrentインフォハッシュ（インデックス付き）
    downloaded: bool = False         # ダウンロード完了
```

## 一般的な操作

### BangumiDatabase

```python
with Database() as db:
    # 作成
    db.bangumi.add(bangumi)              # 単一挿入
    db.bangumi.add_all(bangumi_list)     # バッチ挿入（重複排除）

    # 読み取り
    db.bangumi.search_all()              # 全レコード（キャッシュ、5分TTL）
    db.bangumi.search_id(123)            # IDで検索
    db.bangumi.match_torrent("torrent name")  # title_rawマッチで検索
    db.bangumi.not_complete()            # 未完了シリーズ
    db.bangumi.get_needs_review()        # レビューフラグ付き

    # 更新
    db.bangumi.update(bangumi)           # 単一レコード更新
    db.bangumi.update_all(bangumi_list)  # バッチ更新

    # 削除
    db.bangumi.delete_one(123)           # ハード削除
    db.bangumi.disable_rule(123)         # ソフト削除（deleted=True）
```

### RSSDatabase

```python
with Database() as db:
    # 作成
    db.rss.add(rss_item)                 # 単一挿入
    db.rss.add_all(rss_items)            # バッチ挿入（重複排除）

    # 読み取り
    db.rss.search_all()                  # 全フィード
    db.rss.search_active()               # 有効なフィードのみ
    db.rss.search_aggregate()            # 有効 + aggregate=True

    # 更新
    db.rss.update(id, rss_update)        # 部分更新
    db.rss.enable(id)                    # フィード有効化
    db.rss.disable(id)                   # フィード無効化
    db.rss.enable_batch([1, 2, 3])       # バッチ有効化
    db.rss.disable_batch([1, 2, 3])      # バッチ無効化
```

### TorrentDatabase

```python
with Database() as db:
    # 作成
    db.torrent.add(torrent)              # 単一挿入
    db.torrent.add_all(torrents)         # バッチ挿入

    # 読み取り
    db.torrent.search_all()              # 全トレント
    db.torrent.search_by_qb_hash(hash)   # qBittorrentハッシュで検索
    db.torrent.search_by_url(url)        # URLで検索
    db.torrent.check_new(torrents)       # 既存のものをフィルター

    # 更新
    db.torrent.update_qb_hash(id, hash)  # qb_hashを設定
```

## キャッシング

### Bangumiキャッシュ

`search_all()`の結果はモジュールレベルで5分のTTLでキャッシュされます：

```python
# bangumi.pyのモジュールレベルキャッシュ
_bangumi_cache: list[Bangumi] | None = None
_bangumi_cache_time: float = 0
_BANGUMI_CACHE_TTL: float = 300.0  # 5分

# キャッシュ無効化
def _invalidate_bangumi_cache():
    global _bangumi_cache, _bangumi_cache_time
    _bangumi_cache = None
    _bangumi_cache_time = 0
```

**重要：** キャッシュは以下で自動的に無効化されます：
- `add()`、`add_all()`
- `update()`、`update_all()`
- `delete_one()`、`delete_all()`
- `archive_one()`、`unarchive_one()`
- 任意のRSSリンク更新操作

### セッションExpunge

キャッシュされたオブジェクトは`DetachedInstanceError`を防ぐためにセッションから**expunge**されます：

```python
for b in bangumis:
    self.session.expunge(b)  # セッションから切り離す
```

## マイグレーションシステム

### スキーマバージョニング

マイグレーションは`schema_version`テーブルを介して追跡されます：

```python
CURRENT_SCHEMA_VERSION = 7

# 各マイグレーション：(バージョン、説明、[SQLステートメント])
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

### 新しいマイグレーションの追加

1. `combine.py`の`CURRENT_SCHEMA_VERSION`をインクリメント
2. `MIGRATIONS`リストにマイグレーションタプルを追加：

```python
MIGRATIONS = [
    # ... 既存のマイグレーション ...
    (
        8,
        "add my_new_column to bangumi",
        [
            "ALTER TABLE bangumi ADD COLUMN my_new_column TEXT DEFAULT NULL",
        ],
    ),
]
```

3. `run_migrations()`に冪等性チェックを追加：

```python
if "bangumi" in tables and version == 8:
    columns = [col["name"] for col in inspector.get_columns("bangumi")]
    if "my_new_column" in columns:
        needs_run = False
```

4. `module/models/`の対応するPydanticモデルを更新

### デフォルト値のバックフィル

マイグレーション後、`_fill_null_with_defaults()`がモデルのデフォルトに基づいてNULL値を自動的に埋めます：

```python
# モデルが定義している場合：
class Bangumi(SQLModel, table=True):
    my_field: bool = False

# NULLの既存行はFalseに更新されます
```

## パフォーマンスパターン

### バッチクエリ

`add_all()`は、Nクエリの代わりに単一のクエリを使用して重複をチェックします：

```python
# 効率的：単一SELECT
keys_to_check = [(d.title_raw, d.group_name) for d in datas]
conditions = [
    and_(Bangumi.title_raw == tr, Bangumi.group_name == gn)
    for tr, gn in keys_to_check
]
statement = select(Bangumi.title_raw, Bangumi.group_name).where(or_(*conditions))
```

### 正規表現マッチング

`match_list()`は、すべてのタイトルマッチ用に単一の正規表現パターンをコンパイルします：

```python
# 一度コンパイル、多くマッチ
sorted_titles = sorted(title_index.keys(), key=len, reverse=True)
pattern = "|".join(re.escape(title) for title in sorted_titles)
title_regex = re.compile(pattern)

# トレントごとにO(n)ではなくO(1)ルックアップ
for torrent in torrent_list:
    match = title_regex.search(torrent.name)
```

### インデックス付きカラム

以下のカラムには高速ルックアップ用のインデックスがあります：

| テーブル | カラム | インデックスタイプ |
|---------|--------|------------------|
| `bangumi` | `title_raw` | 通常 |
| `bangumi` | `deleted` | 通常 |
| `bangumi` | `archived` | 通常 |
| `rssitem` | `url` | ユニーク |
| `torrent` | `name` | 通常 |
| `torrent` | `url` | ユニーク |
| `torrent` | `qb_hash` | 通常 |

## テスト

### テストデータベースセットアップ

テストはインメモリSQLiteデータベースを使用します：

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

### ファクトリ関数

テストデータ作成にはファクトリ関数を使用：

```python
from test.factories import make_bangumi, make_torrent, make_rss_item

def test_bangumi_search():
    bangumi = make_bangumi(title_raw="Test Title", season=2)
    # ... テストロジック
```

## 設計ノート

### 外部キーなし

SQLite外部キー強制はデフォルトで無効になっています。リレーションシップ（`Torrent.bangumi_id`など）はデータベース制約ではなくアプリケーションロジックで管理されます。

### ソフト削除

`Bangumi.deleted`フラグはソフト削除を可能にします。クエリはユーザー向けデータには`deleted=False`でフィルターする必要があります：

```python
statement = select(Bangumi).where(Bangumi.deleted == false())
```

### トレントタグ付け

トレントはリネーム操作中のオフセットルックアップ用にqBittorrentで`ab:{bangumi_id}`でタグ付けされます。これにより、データベースクエリなしで高速な番組識別が可能になります。

## 一般的な問題

### DetachedInstanceError

キャッシュされたオブジェクトを別のセッションからアクセスする場合：

```python
# 間違い：新しいセッションでキャッシュされたオブジェクトにアクセス
bangumis = db.bangumi.search_all()  # キャッシュ済み
with Database() as new_db:
    new_db.session.add(bangumis[0])  # エラー！

# 正しい：オブジェクトはexpungeされ、独立して動作
bangumis = db.bangumi.search_all()
bangumis[0].title_raw = "New Title"  # OK、ただし永続化されない
```

### キャッシュの古さ

手動SQLアップデートがORMをバイパスする場合、キャッシュを無効化：

```python
from module.database.bangumi import _invalidate_bangumi_cache

with engine.connect() as conn:
    conn.execute(text("UPDATE bangumi SET ..."))
    conn.commit()

_invalidate_bangumi_cache()  # 重要！
```

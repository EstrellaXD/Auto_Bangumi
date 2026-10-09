# データベース開発ガイド

このページでは、AutoBangumi バックエンドのデータ層（エンジン、`Database` ファサード、リポジトリ、セッションの規約、スキーマのマイグレーション）を説明します。コードは `backend/src/module/database/` にあります。

## 概要

- データベースは SQLite ファイル `data/data.db`、ORM は SQLModel（Pydantic + SQLAlchemy）です。
- アプリケーション全体で非同期エンジン `sqlite+aiosqlite` だけを使います。各接続で `PRAGMA journal_mode=WAL`、`busy_timeout=5000`、`foreign_keys=ON` を設定します。複数の接続が同時に書き込め、競合した書き込みはすぐに `database is locked` を出さずに待ちます。
- 外部キー制約は有効です。ほかの行から参照されている行を削除する前に、参照している行を先に処理してください（例えば `BangumiDatabase.delete_all` は先にトレント記録を削除します）。

```
module/database/
├── __init__.py          # Database、get_db（FastAPI の依存）
├── engine.py            # async_engine、async_session_factory、接続ごとの PRAGMA
├── combine.py           # Database：1 つのセッションとすべてのリポジトリ
├── migrations.py        # MIGRATIONS テーブルとマイグレーションの実行
├── bangumi.py、rss.py、torrent.py、movie.py、user.py、auth.py、
├── inbox.py、llm_credential.py、rename_operation.py、aria2.py、
└── plugin_kv.py、passkey.py   # テーブルごとのリポジトリ
```

## Database とセッション

`Database` は非同期コンテキストマネージャーです。`AsyncSession` を 1 つ作り、リポジトリを自身の属性として持ちます。`async with` ブロックを出るとセッションを閉じます。

```python
from module.database import Database

async with Database() as db:
    rules = await db.bangumi.search_all()
    feeds = await db.rss.search_all()
```

| 属性 | リポジトリ | テーブル |
| --- | --- | --- |
| `db.bangumi` | `BangumiDatabase` | `bangumi` |
| `db.rss` | `RSSDatabase` | `rssitem` |
| `db.torrent` | `TorrentDatabase` | `torrent` |
| `db.movie` | `MovieDatabase` | `movie` |
| `db.user` | `UserDatabase` | `user` |
| `db.auth` | `AuthDatabase` | `auth_session`、`api_token` |
| `db.inbox` | `InboxDatabase` | 通知センター |
| `db.llm_credential` | `LLMCredentialDatabase` | LLM のサブスクリプション認証情報 |
| `db.rename_operation` | `RenameOperationDatabase` | `rename_operation`（リネームの競合と進捗） |
| `db.aria2` | `Aria2GidDatabase` | `aria2_gid` |
| `db.plugin_kv` | `PluginKVDatabase` | `plugin_kv`（プラグインの `ctx.kv`） |

`PasskeyDatabase` は `Database` に含まれません。必要なときに `PasskeyDatabase(db.session)` で作ります。

`Database` はいくつかのセッションメソッドも転送します：`add`（同期。キューに入れるだけ）、`commit`、`rollback`、`refresh`、`close`。`begin_write()` は SQLite では `BEGIN IMMEDIATE` を実行します。「読んでから書き、その間に不変条件を保つ」場合に使い、そのセッションで最初にアクセスする前に呼び出します。

### セッションの規約

**1 つの操作に 1 つのセッション。** 1 回のリクエストや 1 回のループより長く生きるオブジェクトに、セッションや `Database` を保存しないでください。`AppContext` はセッションを持ちません。

- ルートでは依存性注入を使います。

  ```python
  from fastapi import Depends
  from module.database import Database, get_db

  @router.get("/example")
  async def example(db: Database = Depends(get_db)):
      return await db.bangumi.search_all()
  ```

- 定期ループとサービスは、実行のたびに自分で開きます：`async with Database() as db:`。
- サービスは依存をコンストラクタで受け取ります：`RSSEngine(db)`、`TorrentManager(db)`。サービス内では `self.db.<リポジトリ>` を使い、リポジトリを 1 つだけ使う呼び出し側は `db.<リポジトリ>` を直接使います。
- セッションファクトリは `expire_on_commit=False` です。コミット後もオブジェクトの属性は読めますが、そのオブジェクトは新しいセッションには関連付いていません。変更するときは、新しいセッションでもう一度取得してください。

## リポジトリ

リポジトリは `AsyncSession` を受け取り、メソッドはすべて `async def` で、多くはメソッドの中でコミットします。クエリを追加するときは：

- そのテーブルのリポジトリに置きます。ルートやサービスに SQL を直接書かないでください。
- 複数行は `in_` で 1 回で取得します。ループの中で 1 行ずつ問い合わせないでください。
- 論理削除：`bangumi` と `movie` には `deleted` フィールドがあります。ルールの「無効化」（`disable_rule`）は `deleted` を `True` にするだけで、行を本当に削除するのは `delete_one` です。有効なルールを問い合わせるときは `deleted` で絞り込んでください。

### 複数のダウンローダー

4.0 はダウンローダーのインスタンスを複数持てます（設定 `plugins.instances`）。`bangumi`、`movie`、`rssitem`、`torrent` には `downloader_id` 列があります。

- ルールとフィードでは、空は「既定のインスタンスを使う」（`plugins.slots.downloader`）という意味です。
- トレント記録では、そのトレントが実際にあるインスタンスです。3.3 から引き継いだトレントは `default` です。

## スキーマのマイグレーション

マイグレーションは `migrations.py` の `MIGRATIONS` タプルにあり、テーブル駆動で実行されます。データベースの `schema_version` テーブルが適用済みのバージョンを記録します。

```python
Migration(
    26,
    "add downloader_id to bangumi, movie, rssitem and torrent",
    (...SQL 文...),
    already_applied=...,          # ガード：このマイグレーションがすでに有効か
    guarded_statements=(...),     # 任意：文ごとのガード
)
```

起動時、AB はまず `SQLModel.metadata.create_all` を実行し、次に `run_migrations()` を実行します。

1. `schema_version` を読み、そのバージョン以下のマイグレーションを飛ばします。
2. 未適用のマイグレーションごとにデータベースの構造を調べ直し、ガードを呼びます。すでに有効な場合（例えば新しいデータベースを `create_all` がモデルから作った場合）は、バージョンだけを記録します。
3. そうでなければ、1 つの SAVEPOINT の中で文を実行します。どれかが失敗すると、そのマイグレーションをロールバックして例外を上に投げ、マイグレーションのトランザクション全体がロールバックされ、AB は起動に失敗します。AB は途中までしか移行していないスキーマでは動きません。
4. マイグレーションを実行した場合は、最後に既存の行の `NULL` をモデルの既定値で埋めます（`fill_null_with_defaults_conn`）。主キー、`default_factory` のフィールド、既定値が `None` の Optional フィールドは対象外です。

### マイグレーションを追加する

1. 先に `module/models/` のモデルを変更します。新しいデータベースは `create_all` で新しい構造になります。
2. `MIGRATIONS` の末尾に `Migration` を追加します。バージョンは直前の値に 1 を足したものです。`CURRENT_SCHEMA_VERSION` はリストから求まるので、手で変更しないでください。
3. `already_applied` ガードを指定します：`column_exists(テーブル, 列)`、`table_exists(テーブル)`、`index_exists(テーブル, インデックス)`。条件を組み合わせるには `all_checks(...)` を使います。1 つのマイグレーションで複数のテーブルを変更し、テーブルごとに状態が違う可能性がある場合は、`guarded_statements` で文ごとにガードを付けます。
4. `backend/src/test/` にマイグレーションのテストを追加します。古いスキーマから始め、マイグレーションを実行して結果を確認します。

```python
Migration(
    27,
    "add note to bangumi",
    ("ALTER TABLE bangumi ADD COLUMN note TEXT DEFAULT ''",),
    column_exists("bangumi", "note"),
)
```

## テスト

`backend/src/test/conftest.py` にインメモリのデータベースがあります。

- `db_engine`：`sqlite+aiosqlite://` と `StaticPool`。テストごとに新しく作り、モデルからテーブルを作成します。
- `db_session`：`db_engine` に結び付いた `AsyncSession`。

リポジトリを直接テストするときは、`Database(engine=db_engine)` を使うか、`db_session` からリポジトリを 1 つ作ります。

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

バックエンドの pytest は `asyncio_mode = "auto"` なので、非同期のテスト関数に追加のデコレーターは不要です。実行するには：`cd backend && uv run pytest src/test/test_xxx.py -v`。

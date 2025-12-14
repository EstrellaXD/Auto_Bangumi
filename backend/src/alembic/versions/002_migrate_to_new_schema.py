"""migrate to new schema

Revision ID: 002
Revises: 001
Create Date: 2024-12-13

迁移内容：
- Bangumi: filter -> exclude_filter, 新增 include_filter/parser/tmdb_id/bangumi_id/mikan_id, 删除 save_path
- Torrent: 主键从 id 改为 url, 外键解引用为直接值
- RSSItem: 添加 url 索引
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ========== 1. Bangumi 表变更 ==========
    with op.batch_alter_table("bangumi") as batch_op:
        # 重命名 filter -> exclude_filter
        batch_op.alter_column("filter", new_column_name="exclude_filter")
        # 新增字段
        batch_op.add_column(sa.Column("include_filter", sa.String(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("parser", sa.String(), server_default="mikan", nullable=False))
        batch_op.add_column(sa.Column("tmdb_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("bangumi_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("mikan_id", sa.String(), nullable=True))
        # 删除字段
        batch_op.drop_column("save_path")

    # ========== 2. Torrent 表重建 ==========
    # 由于主键变更（id -> url），需要完全重建表

    # 2.1 读取旧数据和关联信息
    old_torrents = conn.execute(sa.text("""
        SELECT t.id, t.bangumi_id, t.rss_id, t.name, t.url, t.homepage, t.downloaded,
               b.official_title, b.season, b.rss_link as bangumi_rss_link,
               r.url as rss_url
        FROM torrent t
        LEFT JOIN bangumi b ON t.bangumi_id = b.id
        LEFT JOIN rssitem r ON t.rss_id = r.id
    """)).fetchall()

    # 2.2 删除旧表
    op.drop_table("torrent")

    # 2.3 创建新表
    op.create_table(
        "torrent",
        sa.Column("url", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("downloaded", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("renamed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("download_uid", sa.String(), nullable=True),
        sa.Column("bangumi_official_title", sa.String(), nullable=False, server_default=""),
        sa.Column("bangumi_season", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rss_link", sa.String(), nullable=False, server_default=""),
        sa.Column("homepage", sa.String(), nullable=True),
    )

    # 2.4 创建索引
    op.create_index("ix_torrent_created_at", "torrent", ["created_at"])
    op.create_index("ix_torrent_download_uid", "torrent", ["download_uid"])
    op.create_index("ix_torrent_bangumi_official_title", "torrent", ["bangumi_official_title"])
    op.create_index("ix_torrent_bangumi_season", "torrent", ["bangumi_season"])
    op.create_index("ix_torrent_rss_link", "torrent", ["rss_link"])

    # 2.5 迁移数据（去重，以 url 为主键）
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()

    for row in old_torrents:
        (id_, bangumi_id, rss_id, name, url, homepage, downloaded,
         official_title, season, bangumi_rss_link, rss_url) = row

        # 跳过重复的 URL
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # 确定 rss_link
        rss_link = bangumi_rss_link or rss_url or ""

        conn.execute(
            sa.text("""
                INSERT INTO torrent (url, name, created_at, downloaded, renamed,
                                     download_uid, bangumi_official_title, bangumi_season,
                                     rss_link, homepage)
                VALUES (:url, :name, :created_at, :downloaded, :renamed,
                        :download_uid, :official_title, :season, :rss_link, :homepage)
            """),
            {
                "url": url,
                "name": name or "",
                "created_at": now,
                "downloaded": 1 if downloaded else 0,
                "renamed": 1,  # 假设旧数据都已重命名
                "download_uid": None,
                "official_title": official_title or "",
                "season": season or 1,
                "rss_link": rss_link,
                "homepage": homepage,
            }
        )

    # ========== 3. RSSItem 表 - 添加索引 ==========
    with op.batch_alter_table("rssitem") as batch_op:
        batch_op.create_index("ix_rssitem_url", ["url"])


def downgrade() -> None:
    """回滚（不推荐，会丢失数据）"""
    # Torrent 表回滚需要重建，但外键信息已丢失，无法完全恢复
    pass

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# 添加路径
src_dir = Path(__file__).resolve().parent.parent  # backend/src
sys.path.insert(0, str(src_dir))

# 导入所有模型（确保它们被注册到 metadata）
from models import Bangumi, RSSItem, Torrent, User

# Alembic Config 对象
config = context.config

# 设置日志 - 注意：在程序内部调用时不要重置日志配置
# fileConfig 会破坏 uvicorn 的日志处理器，导致启动失败
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# SQLModel 的 metadata
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """离线模式运行迁移"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite 必需
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移"""
    # 创建 data 目录
    data_dir = src_dir.parent / "data"  # backend/data
    data_dir.mkdir(exist_ok=True)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite 必需
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

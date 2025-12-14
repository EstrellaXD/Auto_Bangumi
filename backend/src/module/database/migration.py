"""
数据库版本管理和迁移系统 - 使用 Alembic
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from .engine import DATA_PATH, engine

logger = logging.getLogger(__name__)

# backend 目录路径
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent


def get_alembic_config() -> Config:
    """获取 Alembic 配置"""
    alembic_ini = BACKEND_DIR / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    return alembic_cfg


def get_current_revision() -> str | None:
    """获取当前数据库的 Alembic 版本"""
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        return context.get_current_revision()


def create_backup() -> Path | None:
    """创建数据库备份"""
    try:
        db_path = Path(DATA_PATH.replace("sqlite:///", ""))
        if db_path.exists():
            backup_path = db_path.parent / f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, backup_path)
            logger.info(f"数据库备份创建: {backup_path}")
            return backup_path
    except Exception as e:
        logger.warning(f"创建备份失败: {e}")
    return None


def check_and_upgrade_database() -> bool:
    """使用 Alembic 检查并升级数据库"""
    try:
        alembic_cfg = get_alembic_config()
        current_rev = get_current_revision()

        logger.info(f"当前数据库版本: {current_rev or '未初始化'}")

        # 检查数据库文件是否存在
        db_path = Path(DATA_PATH.replace("sqlite:///", ""))

        if current_rev is None:
            if db_path.exists() and db_path.stat().st_size > 0:
                # 旧数据库存在但没有 alembic_version 表，先 stamp 到基线
                logger.info("检测到旧数据库，标记为基线版本 001...")
                create_backup()
                command.stamp(alembic_cfg, "001")
                current_rev = "001"
            else:
                # 全新数据库，直接升级会创建所有表
                logger.info("全新数据库，将创建所有表...")

        # 执行迁移到最新版本
        logger.info("执行数据库迁移...")
        command.upgrade(alembic_cfg, "head")
        new_rev = get_current_revision()
        logger.info(f"数据库迁移完成，当前版本: {new_rev}")
        return True

    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        return False


def downgrade_database(revision: str = "-1") -> bool:
    """降级数据库到指定版本"""
    try:
        alembic_cfg = get_alembic_config()
        current_rev = get_current_revision()

        logger.info(f"当前版本: {current_rev}，降级到: {revision}")
        create_backup()

        command.downgrade(alembic_cfg, revision)

        new_rev = get_current_revision()
        logger.info(f"数据库降级完成，当前版本: {new_rev}")

        return True

    except Exception as e:
        logger.error(f"数据库降级失败: {e}")
        return False


def get_migration_history() -> list[dict]:
    """获取迁移历史"""
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            rows = result.fetchall()
            return [{"version": row[0]} for row in rows]
    except Exception as e:
        logger.warning(f"获取迁移历史失败: {e}")
        return []

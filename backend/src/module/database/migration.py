"""
数据库版本管理和迁移系统
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

from sqlmodel import Session, text

from module.conf import DATA_PATH
from module.database.engine import engine
from module.models import DatabaseVersion

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """数据库迁移管理器"""

    def __init__(self, engine=engine):
        self.engine = engine
        self.current_app_version = self._get_app_version()
        self.migration_history: dict[str, Callable] = {
            "3.2.0": self._migrate_to_3_2_0,
            # 在这里添加新版本的迁移函数
        }

    def _get_app_version(self) -> str:
        """获取应用程序版本"""
        try:
            from module.__version__ import VERSION

            return VERSION
        except ImportError as e:
            logger.warning(f"无法读取版本信息: {e}")
            return "unknown"

    def _ensure_version_table(self, session: Session):
        """确保版本表存在"""
        try:
            # 检查版本表是否存在
            result = session.exec(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='databaseversion'"
                )
            ).first()

            if not result:
                logger.info("创建数据库版本表...")
                DatabaseVersion.metadata.create_all(self.engine)

                # 记录当前版本作为基础版本
                initial_version = DatabaseVersion(
                    version="3.1.18", description="初始数据库版本"
                )
                session.add(initial_version)
                session.commit()
                logger.info(f"初始化数据库版本: {self.current_app_version}")

        except Exception as e:
            logger.error(f"创建版本表失败: {e}")
            raise

    def get_current_db_version(self) -> str:
        """获取当前数据库版本"""
        with Session(self.engine) as session:
            self._ensure_version_table(session)

            try:
                # 获取最新的数据库版本
                result = session.exec(
                    text(
                        "SELECT version FROM databaseversion ORDER BY applied_at DESC LIMIT 1"
                    )
                ).first()

                return result[0] if result else "3.1.18"
            except Exception as e:
                logger.warning(f"获取数据库版本失败: {e}")
                return "unknown"

    def check_compatibility(self) -> dict[str, any]:
        """检查数据库兼容性"""
        db_version = self.get_current_db_version()
        app_version = self.current_app_version

        result = {
            "db_version": db_version,
            "app_version": app_version,
            "compatible": False,
            "needs_upgrade": False,
            "needs_downgrade": False,
            "available_migrations": [],
            "message": "",
        }

        if db_version == "unknown":
            result["message"] = "无法确定数据库版本，建议重新初始化"
            result["needs_upgrade"] = True
        elif db_version == app_version:
            result["compatible"] = True
            result["message"] = "数据库版本与应用版本匹配"
        else:
            # 检查是否有可用的迁移路径
            available_migrations = self._get_migration_path(db_version, app_version)
            result["available_migrations"] = available_migrations

            if available_migrations:
                result["needs_upgrade"] = True
                result["message"] = f"需要从 {db_version} 升级到 {app_version}"
            else:
                result["message"] = f"不支持从 {db_version} 到 {app_version} 的迁移"

        return result

    def _get_migration_path(self, from_version: str, to_version: str) -> list[str]:
        """获取迁移路径"""
        available_versions = list(self.migration_history.keys())

        # 找出所有需要升级的版本（大于from_version且小于等于to_version）
        migrations_needed = []

        for version in available_versions:
            if (
                self._version_compare(version, from_version) > 0
                and self._version_compare(version, to_version) <= 0
            ):
                migrations_needed.append(version)

        # 按版本号排序
        migrations_needed.sort(key=lambda v: self._version_to_tuple(v))

        return migrations_needed

    def _version_compare(self, version1: str, version2: str) -> int:
        """比较两个版本号
        返回值: 1 表示 version1 > version2, 0 表示相等, -1 表示 version1 < version2
        """
        v1_tuple = self._version_to_tuple(version1)
        v2_tuple = self._version_to_tuple(version2)

        if v1_tuple > v2_tuple:
            return 1
        elif v1_tuple < v2_tuple:
            return -1
        else:
            return 0

    def _version_to_tuple(self, version: str) -> tuple:
        """将版本字符串转换为可比较的元组"""
        try:
            # 处理类似 "3.2.0" 的版本号
            parts = version.split(".")
            return tuple(int(part) for part in parts)
        except (ValueError, AttributeError):
            # 如果解析失败，返回一个默认值
            return (0, 0, 0)

    def _migrate_to_3_2_0(self, session: Session):
        """迁移到版本 3.2.0"""
        logger.info("开始迁移到版本 3.2.0")

        try:
            from module.database.combine import Database
            from module.models.torrent import Torrent
            from module.utils import get_hash

            # 先执行标准迁移
            db = Database(self.engine)
            db.migrate()
            logger.info("标准数据库迁移完成")

            # 然后更新torrent表的特殊字段
            logger.info("更新Torrent表的特殊字段...")
            try:
                # 获取所有torrent记录
                torrents = db.torrent.search_all()

                updated_count = 0
                for torrent in torrents:
                    try:
                        # 设置renamed为True
                        torrent.renamed = True

                        # 通过URL获取download_uid
                        if torrent.url:
                            hash_value = get_hash(torrent.url)
                            torrent.download_uid = hash_value
                            logger.debug(
                                f"为torrent {torrent.url} 设置download_uid: {hash_value}"
                            )

                        db.merge(torrent)
                        updated_count += 1

                    except Exception as e:
                        logger.warning(f"更新torrent记录失败: {e}")
                        continue

                db.commit()
                logger.info(f"成功更新 {updated_count} 个torrent记录")

            except Exception as e:
                logger.warning(f"更新Torrent特殊字段时出错: {e}")

            # 清理Bangumi表的rss_link字段
            logger.info("清理Bangumi表的rss_link字段...")
            try:
                # 获取所有bangumi记录
                bangumis = db.bangumi.search_all()

                updated_count = 0
                for bangumi in bangumis:
                    try:
                        if bangumi.rss_link:
                            # 移除rss_link中的特定字符（根据需要修改这里的清理逻辑）
                            original_link = bangumi.rss_link
                            # 示例：移除某些字符或进行其他清理
                            cleaned_link = bangumi.rss_link.replace(",", "").strip()

                            if original_link != cleaned_link:
                                bangumi.rss_link = cleaned_link
                                db.merge(bangumi)
                                updated_count += 1
                                logger.debug(
                                    f"清理bangumi {bangumi.official_title} 的rss_link: {original_link} -> {cleaned_link}"
                                )

                    except Exception as e:
                        logger.warning(f"清理bangumi rss_link记录失败: {e}")
                        continue

                db.commit()
                logger.info(f"成功清理 {updated_count} 个bangumi的rss_link记录")

            except Exception as e:
                logger.warning(f"清理Bangumi rss_link字段时出错: {e}")

            # 更新Bangumi表的parser字段，从RSS表获取
            logger.info("更新Bangumi表的parser字段...")
            try:
                # 获取所有bangumi记录
                bangumis = db.bangumi.search_all()

                updated_count = 0
                for bangumi in bangumis:
                    try:
                        if bangumi.rss_link:
                            # 从RSS表中查找对应的parser
                            rss_item = db.rss.search_url(bangumi.rss_link)
                            if rss_item and rss_item.parser:
                                if bangumi.parser != rss_item.parser:
                                    bangumi.parser = rss_item.parser
                                    db.merge(bangumi)
                                    updated_count += 1
                                    logger.debug(
                                        f"更新bangumi {bangumi.official_title} 的parser: {rss_item.parser}"
                                    )
                            elif not bangumi.parser or bangumi.parser == "":
                                # 如果RSS表中没有找到对应记录，设置默认parser
                                bangumi.parser = "mikan"
                                db.merge(bangumi)
                                updated_count += 1
                                logger.debug(
                                    f"设置bangumi {bangumi.official_title} 默认parser: mikan"
                                )

                    except Exception as e:
                        logger.warning(f"更新bangumi parser记录失败: {e}")
                        continue

                db.commit()
                logger.info(f"成功更新 {updated_count} 个bangumi的parser记录")

            except Exception as e:
                logger.warning(f"更新Bangumi parser字段时出错: {e}")

            logger.info("成功迁移到版本 3.2.0")
        except Exception as e:
            logger.error(f"迁移到版本 3.2.0 失败: {e}")
            raise

    def perform_migration(self, target_version: str = None) -> bool:
        """执行数据库迁移"""
        if target_version is None:
            target_version = self.current_app_version

        compatibility = self.check_compatibility()

        if compatibility["compatible"]:
            logger.info("数据库已是最新版本，无需迁移")
            return True

        if not compatibility["needs_upgrade"]:
            logger.error(f"不支持的迁移: {compatibility['message']}")
            return False

        migrations = compatibility["available_migrations"]
        if not migrations:
            logger.error("没有可用的迁移路径")
            return False

        logger.info(
            f"开始数据库迁移: {compatibility['db_version']} -> {target_version}"
        )

        with Session(self.engine) as session:
            try:
                # 创建备份
                self._create_backup()

                # 执行迁移
                for version in migrations:
                    logger.info(f"应用迁移: {version}")

                    if version in self.migration_history:
                        migration_func = self.migration_history[version]
                        migration_func(session)

                        # 记录迁移历史
                        version_record = DatabaseVersion(
                            version=version, description=f"迁移到版本 {version}"
                        )
                        session.add(version_record)
                        session.commit()

                        logger.info(f"成功应用迁移: {version}")
                    else:
                        logger.warning(f"跳过未定义的迁移: {version}")

                logger.info("数据库迁移完成")
                return True

            except Exception as e:
                logger.error(f"迁移失败: {e}")
                session.rollback()
                # 这里可以添加从备份恢复的逻辑
                return False

    def _create_backup(self):
        """创建数据库备份"""
        try:
            db_path = Path(DATA_PATH.replace("sqlite:///", ""))
            if db_path.exists():
                backup_path = (
                    db_path.parent
                    / f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                )
                import shutil

                shutil.copy2(db_path, backup_path)
                logger.info(f"数据库备份创建: {backup_path}")
        except Exception as e:
            logger.warning(f"创建备份失败: {e}")

    def _rebuild_tables_if_needed(self, session: Session, existing_tables: dict):
        """根据需要重建表结构"""
        from module.database.combine import Database

        # 使用现有的迁移逻辑
        db = Database(self.engine)
        db.migrate()

    def force_rebuild(self) -> bool:
        """强制重建数据库"""
        logger.warning("开始强制重建数据库...")

        try:
            # 创建备份
            self._create_backup()

            with Session(self.engine) as session:
                from module.database.combine import Database

                # 重建数据库
                db = Database(self.engine)
                db.migrate()

                # 更新版本记录
                self._ensure_version_table(session)
                version_record = DatabaseVersion(
                    version=self.current_app_version, description="强制重建数据库"
                )
                session.add(version_record)
                session.commit()

            logger.info("数据库重建完成")
            return True

        except Exception as e:
            logger.error(f"数据库重建失败: {e}")
            return False


def check_and_upgrade_database() -> bool:
    """检查并升级数据库的主入口函数"""
    try:
        migration = DatabaseMigration()
        compatibility = migration.check_compatibility()

        logger.info(f"数据库兼容性检查: {compatibility}")

        if compatibility["compatible"]:
            logger.info("数据库版本兼容，无需升级")
            return True
        elif compatibility["needs_upgrade"]:
            logger.info("检测到需要数据库升级")
            return migration.perform_migration()
        else:
            logger.error("数据库版本不兼容且无法升级")
            return False

    except Exception as e:
        logger.error(f"数据库检查失败: {e}")
        return False


if __name__ == "__main__":
    # 测试迁移系统
    logging.basicConfig(level=logging.INFO)

    migration = DatabaseMigration()
    compatibility = migration.check_compatibility()

    print("=== 数据库兼容性检查 ===")
    for key, value in compatibility.items():
        print(f"{key}: {value}")

    if compatibility["needs_upgrade"]:
        print("\n=== 开始数据库升级 ===")
        success = migration.perform_migration()
        print(f"升级结果: {'成功' if success else '失败'}")

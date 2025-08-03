import logging
from datetime import datetime

from sqlmodel import Session, select

from module.models import DatabaseVersion

logger = logging.getLogger(__name__)


class VersionDatabase:
    """数据库版本管理类"""

    def __init__(self, session: Session):
        self.session = session

    def add(self, version: str, description: str = "") -> bool:
        """添加新的数据库版本记录"""
        try:
            version_record = DatabaseVersion(
                version=version, description=description, applied_at=datetime.utcnow()
            )
            self.session.add(version_record)
            self.session.commit()
            self.session.refresh(version_record)
            logger.debug(f"[Database] Insert version {version} into database.")
            return True
        except Exception as e:
            logger.error(f"[Database] Failed to add version {version}: {e}")
            self.session.rollback()
            return False

    def get_current_version(self) -> str | None:
        """获取当前最新的数据库版本"""
        try:
            statement = select(DatabaseVersion).order_by(
                DatabaseVersion.applied_at.desc()
            )
            latest_version = self.session.exec(statement).first()
            if latest_version:
                logger.debug(f"[Database] Current version: {latest_version.version}")
                return latest_version.version
            else:
                logger.debug("[Database] No version records found.")
                return None
        except Exception as e:
            logger.error(f"[Database] Failed to get current version: {e}")
            return None

    def search_all(self) -> list[DatabaseVersion]:
        """获取所有版本记录"""
        try:
            statement = select(DatabaseVersion).order_by(
                DatabaseVersion.applied_at.desc()
            )
            versions = self.session.exec(statement).all()
            logger.debug(f"[Database] Found {len(versions)} version records.")
            return versions
        except Exception as e:
            logger.error(f"[Database] Failed to search all versions: {e}")
            return []

    def search_by_version(self, version: str) -> DatabaseVersion | None:
        """根据版本号查找版本记录"""
        try:
            statement = select(DatabaseVersion).where(
                DatabaseVersion.version == version
            )
            version_record = self.session.exec(statement).first()
            if version_record:
                logger.debug(f"[Database] Found version record: {version}")
                return version_record
            else:
                logger.debug(f"[Database] Version record not found: {version}")
                return None
        except Exception as e:
            logger.error(f"[Database] Failed to search version {version}: {e}")
            return None

    def delete_version(self, version: str) -> bool:
        """删除指定版本记录"""
        try:
            statement = select(DatabaseVersion).where(
                DatabaseVersion.version == version
            )
            version_record = self.session.exec(statement).first()
            if version_record:
                self.session.delete(version_record)
                self.session.commit()
                logger.debug(f"[Database] Deleted version record: {version}")
                return True
            else:
                logger.warning(
                    f"[Database] Version record not found for deletion: {version}"
                )
                return False
        except Exception as e:
            logger.error(f"[Database] Failed to delete version {version}: {e}")
            self.session.rollback()
            return False

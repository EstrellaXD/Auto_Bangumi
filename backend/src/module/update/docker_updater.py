"""
Docker 环境更新器

专门用于 Docker 容器环境中的程序更新。
通过下载新版本、替换文件、退出进程让 Docker 重启来完成更新。
"""

import asyncio
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from module.network.request_url import RequestURL

logger = logging.getLogger(__name__)

# 更新锁文件路径
UPDATE_LOCK_FILE = "/tmp/auto_bangumi_update.lock"

# 允许的下载域名白名单
ALLOWED_DOMAINS = ["github.com", "codeload.github.com"]  # GitHub 的文件下载域名

# 最大下载文件大小 (100MB)
MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024


class DockerUpdater:
    """Docker 环境更新器"""

    def __init__(self):
        self.temp_dir: Optional[Path] = None
        self.backup_dir = Path("/app.bak")
        self.app_dir = Path("/app")

    def _is_url_allowed(self, url: str) -> bool:
        """检查 URL 是否在允许的白名单中

        Args:
            url: 要检查的 URL

        Returns:
            bool: 如果 URL 被允许返回 True
        """
        try:
            parsed = urlparse(url)

            # 只允许 HTTPS 协议
            if parsed.scheme.lower() != "https":
                return False

            domain = parsed.netloc.lower()

            # 检查域名是否在白名单中
            for allowed_domain in ALLOWED_DOMAINS:
                if domain == allowed_domain or domain.endswith(f".{allowed_domain}"):
                    return True

            return False
        except Exception as e:
            logger.error(f"[DockerUpdater] URL parsing error: {e}")
            return False

    def _create_update_lock(self) -> bool:
        """创建更新锁文件，防止并发更新

        Returns:
            bool: 成功创建锁返回 True，已存在锁返回 False
        """
        try:
            if os.path.exists(UPDATE_LOCK_FILE):
                logger.warning("[DockerUpdater] Update already in progress")
                return False

            with open(UPDATE_LOCK_FILE, "w") as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            logger.error(f"[DockerUpdater] Failed to create update lock: {e}")
            return False

    def _remove_update_lock(self):
        """移除更新锁文件"""
        try:
            if os.path.exists(UPDATE_LOCK_FILE):
                os.remove(UPDATE_LOCK_FILE)
        except Exception as e:
            logger.error(f"[DockerUpdater] Failed to remove update lock: {e}")

    async def _download_file(self, url: str) -> Path:
        """下载文件到临时目录

        Args:
            url: 下载 URL

        Returns:
            Path: 下载的文件路径

        Raises:
            Exception: 下载失败时抛出异常
        """
        logger.info(f"[DockerUpdater] Downloading from {url}")

        # 创建临时目录
        self.temp_dir = Path(tempfile.mkdtemp(prefix="auto_bangumi_update_"))
        download_path = self.temp_dir / "update.zip"

        try:
            async with RequestURL() as client:
                # 设置用户代理
                client.header["User-Agent"] = "Auto_Bangumi Docker Updater"

                response = await client.get_url(url, stream=True)

                # 检查文件大小
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
                    raise Exception(f"File too large: {content_length} bytes")

                # 下载文件
                downloaded_size = 0
                with open(download_path, "wb") as f:
                    async for chunk in response.aiter_bytes(8192):
                        downloaded_size += len(chunk)
                        if downloaded_size > MAX_DOWNLOAD_SIZE:
                            raise Exception("Downloaded file exceeds size limit")
                        f.write(chunk)

                logger.info(f"[DockerUpdater] Downloaded {downloaded_size} bytes to {download_path}")
                return download_path

        except Exception as e:
            logger.error(f"[DockerUpdater] Download failed: {e}")
            self._cleanup_temp_files()
            raise

    def _extract_zip(self, zip_path: Path) -> Path:
        """解压 ZIP 文件

        Args:
            zip_path: ZIP 文件路径

        Returns:
            Path: 解压后的目录路径
        """
        extract_path = self.temp_dir / "extracted"
        extract_path.mkdir(exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # 检查 ZIP 文件安全性
                for member in zip_ref.namelist():
                    if member.startswith("/") or ".." in member:
                        raise Exception(f"Unsafe path in zip: {member}")

                zip_ref.extractall(extract_path)

            logger.info(f"[DockerUpdater] Extracted to {extract_path}")

            # 找到实际的程序目录（通常是解压后的第一个子目录）
            extracted_items = list(extract_path.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                return extracted_items[0]
            else:
                return extract_path

        except Exception as e:
            logger.error(f"[DockerUpdater] Extract failed: {e}")
            raise

    def _backup_current_app(self):
        """备份当前应用"""
        try:
            # 删除旧的备份
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)

            # 创建新备份
            shutil.move(str(self.app_dir), str(self.backup_dir))
            logger.info(f"[DockerUpdater] Backed up current app to {self.backup_dir}")

        except Exception as e:
            logger.error(f"[DockerUpdater] Backup failed: {e}")
            raise

    def _install_new_app(self, source_dir: Path):
        """安装新应用

        Args:
            source_dir: 新应用源目录
        """
        try:
            # 移动新应用到目标位置
            shutil.move(str(source_dir), str(self.app_dir))
            logger.info(f"[DockerUpdater] Installed new app from {source_dir}")

        except Exception as e:
            logger.error(f"[DockerUpdater] Installation failed: {e}")
            raise

    def _restore_user_data(self):
        """恢复用户配置和数据"""
        try:
            # 恢复 config 目录
            backup_config = self.backup_dir / "config"
            new_config = self.app_dir / "config"

            if backup_config.exists():
                if new_config.exists():
                    shutil.rmtree(new_config)
                shutil.copytree(backup_config, new_config)
                logger.info("[DockerUpdater] Restored config directory")

            # 恢复 data 目录
            backup_data = self.backup_dir / "data"
            new_data = self.app_dir / "data"

            if backup_data.exists():
                if new_data.exists():
                    shutil.rmtree(new_data)
                shutil.copytree(backup_data, new_data)
                logger.info("[DockerUpdater] Restored data directory")

        except Exception as e:
            logger.error(f"[DockerUpdater] Failed to restore user data: {e}")
            raise

    def _fix_permissions(self):
        """修复文件权限"""
        try:
            # 在 Docker 环境中，使用 chown 命令修复权限
            os.system(f"chown -R ab:ab {self.app_dir}")
            logger.info("[DockerUpdater] Fixed file permissions")

        except Exception as e:
            logger.error(f"[DockerUpdater] Failed to fix permissions: {e}")

    def _rollback(self):
        """回滚到备份版本"""
        try:
            if self.backup_dir.exists():
                if self.app_dir.exists():
                    shutil.rmtree(self.app_dir)
                shutil.move(str(self.backup_dir), str(self.app_dir))
                logger.info("[DockerUpdater] Rolled back to backup version")
            else:
                logger.error("[DockerUpdater] No backup found for rollback")

        except Exception as e:
            logger.error(f"[DockerUpdater] Rollback failed: {e}")

    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("[DockerUpdater] Cleaned up temporary files")
        except Exception as e:
            logger.error(f"[DockerUpdater] Failed to cleanup temp files: {e}")

    async def update(self, download_url: str) -> dict:
        """执行更新

        Args:
            download_url: 更新包下载 URL

        Returns:
            dict: 更新结果
        """
        # 检查 URL
        if not self._is_url_allowed(download_url):
            raise Exception(f"URL not allowed: {download_url}")

        # 创建更新锁
        if not self._create_update_lock():
            raise Exception("Another update is already in progress")

        try:
            logger.info("[DockerUpdater] Starting Docker update process")

            # 1. 下载更新包
            zip_path = await self._download_file(download_url)

            # 2. 解压更新包
            source_dir = self._extract_zip(zip_path)

            # 3. 备份当前应用
            self._backup_current_app()

            # 4. 安装新应用
            self._install_new_app(source_dir)

            # 5. 恢复用户数据
            self._restore_user_data()

            # 6. 修复权限
            self._fix_permissions()

            logger.info("[DockerUpdater] Update completed successfully")

            return {"status": "success", "message": "Update completed, container will restart"}

        except Exception as e:
            logger.error(f"[DockerUpdater] Update failed: {e}")

            # 尝试回滚
            try:
                self._rollback()
            except Exception as rollback_error:
                logger.error(f"[DockerUpdater] Rollback also failed: {rollback_error}")

            raise

        finally:
            # 清理资源
            self._cleanup_temp_files()
            self._remove_update_lock()

    def force_restart(self):
        """强制重启容器（退出进程让 Docker 重启）"""
        logger.info("[DockerUpdater] Forcing container restart")
        # 在 Docker 环境中，.sh 有监控进程会自动重启
        import sys
        sys.exit(0)


# 全局实例
docker_updater = DockerUpdater()


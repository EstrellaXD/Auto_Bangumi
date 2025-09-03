"""
Docker 环境更新器

专门用于 Docker 容器环境中的程序更新。
通过下载新版本、替换文件、退出进程让 Docker 重启来完成更新。
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from module.network.request_url import RequestURL

logger = logging.getLogger(__name__)

# 更新相关文件路径
UPDATE_LOCK_FILE = "/tmp/auto_bangumi_update.lock"
UPDATE_FLAG_FILE = "/tmp/auto_bangumi_update_ready.flag"

# 允许的下载域名白名单
ALLOWED_DOMAINS = ["github.com", "codeload.github.com"]  # GitHub 的文件下载域名

# 最大下载文件大小 (10MB)
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024


class DockerUpdater:
    """Docker 环境更新器"""

    def __init__(self):
        self.temp_dir: Path | None = None
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

                response = await client.get_url(url)

                # 检查文件大小
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
                    raise Exception(f"File too large: {content_length} bytes")

                # 直接获取文件内容
                content = response.content
                if len(content) > MAX_DOWNLOAD_SIZE:
                    raise Exception("Downloaded file exceeds size limit")

                # 写入文件
                with open(download_path, "wb") as f:
                    f.write(content)

                logger.info(f"[DockerUpdater] Downloaded {len(content)} bytes to {download_path}")
                return download_path

        except Exception as e:
            logger.error(f"[DockerUpdater] Download failed: {e}")
            self._cleanup_temp_files()
            raise

    def _create_update_flag(self, download_url: str, extract_path: Path) -> None:
        """创建更新标志文件，供shell脚本检测
        
        Args:
            download_url: 原始下载URL
            extract_path: 解压后的目录路径
        """
        try:
            flag_data = {
                "download_url": download_url,
                "extract_path": str(extract_path),
                "timestamp": asyncio.get_event_loop().time()
            }
            
            with open(UPDATE_FLAG_FILE, "w") as f:
                json.dump(flag_data, f, indent=2)
                
            logger.info(f"[DockerUpdater] Created update flag file: {UPDATE_FLAG_FILE}")
            
        except Exception as e:
            logger.error(f"[DockerUpdater] Failed to create update flag: {e}")
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
            logger.debug(f"[DockerUpdater] Extracted items: {extracted_items}")
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                return extracted_items[0]
            else:
                return extract_path

        except Exception as e:
            logger.error(f"[DockerUpdater] Extract failed: {e}")
            raise




    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("[DockerUpdater] Cleaned up temporary files")
        except Exception as e:
            logger.error(f"[DockerUpdater] Failed to cleanup temp files: {e}")

    async def prepare_update(self, download_url: str) -> dict:
        """准备更新：下载、解压、创建标志文件

        Args:
            download_url: 更新包下载 URL

        Returns:
            dict: 准备结果
        """
        # 检查 URL
        if not self._is_url_allowed(download_url):
            raise Exception(f"URL not allowed: {download_url}")

        # 创建更新锁
        if not self._create_update_lock():
            raise Exception("Another update is already in progress")
            
        try:
            logger.info("[DockerUpdater] Preparing update package")

            # 1. 下载更新包
            zip_path = await self._download_file(download_url)

            # 2. 解压更新包
            source_dir = self._extract_zip(zip_path)

            # 3. 验证解压结果
            if not (source_dir / "src").exists():
                raise Exception("Invalid update package: missing src directory")

            # 4. 创建更新标志文件
            self._create_update_flag(download_url, source_dir)

            logger.info("[DockerUpdater] Update preparation completed")
            return {"status": "success", "message": "Update prepared, process will restart for file replacement"}

        except Exception as e:
            logger.error(f"[DockerUpdater] Update preparation failed: {e}")
            # 清理资源
            self._cleanup_temp_files()
            self._remove_update_lock()
            raise

    def trigger_graceful_restart(self):
        """触发优雅重启：让 Python 进程退出，shell 脚本会检测更新标志并处理"""
        logger.info("[DockerUpdater] Triggering graceful restart for update")
        # 使用退出码 0 让 entrypoint.sh 知道这是正常的重启（热更新）
        sys.exit(0)


# 全局实例
docker_updater = DockerUpdater()

import logging
from pathlib import Path

from module.conf import VERSION, settings
from module.models import Config
from module.update import version_check

logger = logging.getLogger(__name__)


_default_config_dict: dict | None = None


def _get_default_config_dict() -> dict:
    global _default_config_dict
    if _default_config_dict is None:
        _default_config_dict = Config().dict()
    return _default_config_dict


class Checker:
    def __init__(self):
        pass

    @staticmethod
    def check_renamer() -> bool:
        if settings.bangumi_manage.enable:
            return True
        else:
            return False

    @staticmethod
    def check_analyser() -> bool:
        if settings.rss_parser.enable:
            return True
        else:
            return False

    @staticmethod
    def check_first_run() -> bool:
        if Path("config/.setup_complete").exists():
            return False
        return settings.dict() == _get_default_config_dict()

    @staticmethod
    def check_version() -> tuple[bool, int | None]:
        return version_check()

    @staticmethod
    def check_database() -> bool:
        db_path = Path("data/data.db")
        if not db_path.exists():
            return False
        else:
            return True

    @staticmethod
    async def check_downloader_detail() -> tuple[bool, str | None]:
        """下载器可达性检查，附失败原因。

        返回 ``(ok, reason)``；reason 取值 unreachable | credentials | banned，
        成功时为 None。上层（启动等待循环）据此区分「等它启动」和「密码错误，
        等也没用」两类故障。
        """
        from module.downloader import DownloadClient

        # Mock downloader always succeeds
        if settings.downloader.type == "mock":
            logger.info("Using MockDownloader - skipping connection check")
            return True, None

        # Delegate to the concrete client's own auth/capabilities instead of
        # grepping the downloader's homepage HTML (which only ever matches
        # qBittorrent, so aria2 and future backends could never pass).
        # DownloadClient() 的构造本身可能抛（下载器类型无法识别），必须一并
        # 纳入 try——否则一个配置错误会击穿启动等待循环。
        client = None
        try:
            client = DownloadClient()
            async with client as dl_client:
                return dl_client.authed, None
        except ConnectionError:
            logger.error("Downloader connect failed.")
            reason = getattr(client, "last_auth_error", None)
            return False, reason or "unreachable"
        except Exception as e:
            logger.error(f"Downloader connect failed: {e}")
            reason = getattr(client, "last_auth_error", None)
            return False, reason or "unreachable"

    @staticmethod
    async def check_downloader() -> bool:
        ok, _ = await Checker.check_downloader_detail()
        return ok

    @staticmethod
    def check_img_cache() -> bool:
        img_path = Path("data/posters")
        if img_path.exists():
            return True
        else:
            img_path.mkdir()
            return False

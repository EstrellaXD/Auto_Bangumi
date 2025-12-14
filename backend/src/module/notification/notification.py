import importlib
import logging

from module.database import Database
from models import Message
from models.config import Notification
from module.network import load_image
from module.notification.plugin.log import Notifier

logger = logging.getLogger(__name__)


NOTIFICATON_TYPE = ["tetegram", "bark", "server_chan", "wecom", "log"]

_notification_config: Notification | None = None


def get_notification_config() -> Notification:
    """获取通知配置，如果未初始化则返回默认配置"""
    if _notification_config is None:
        return Notification()
    return _notification_config


def set_notification_config(config: Notification):
    """设置通知配置"""
    global _notification_config
    _notification_config = config



class NotificationProcessor:
    """
    通知处理器 - 负责通知数据的解析和格式化
    分离了数据处理逻辑，不直接负责发送
    """

    @staticmethod
    def get_poster_from_db(title: str) -> str:
        """
        从数据库获取番剧海报
        """
        try:
            with Database() as db:
                bangumi = db.bangumi.search_official_title(title)
            return bangumi.poster_link if bangumi and bangumi.poster_link else ""
        except Exception as e:
            logger.error(f"获取海报失败: {title} - {e}")
            return ""

    async def process_notification(self, notify: Message) -> Message:
        """
        处理通知对象，进行必要的数据解析和补充
        """
        # 创建副本，避免修改原对象
        processed = Message(
            title=notify.title,
            season=notify.season,
            episode=notify.episode,
            poster_path=notify.poster_path,
            message=notify.message,
        )
        # 想了想,对每个通知直接传file和post_link, 这样就可以直接用来发送了
        # 生成默认消息
        if processed.episode:
            processed.message = (
                f"番剧名称：{processed.title}\n季度：第{processed.season}季\n更新集数：第{processed.episode}集"
            )
            # 获取海报
            if not processed.poster_path and processed.title:
                logger.debug(f"[NotificationProcessor] 获取海报: {processed.title}")
                processed.poster_path = self.get_poster_from_db(processed.title)

        processed.file = await load_image(processed.poster_path) if processed.poster_path else None

        return processed


class PostNotification:
    """
    使用新的 NotificationManager 进行管理
    """

    def __init__(self) -> None:
        self.processor: NotificationProcessor = NotificationProcessor()
        self.notifier:Notifier = Notifier(**self.config.model_dump())

    @property
    def config(self) -> Notification:
        return get_notification_config()

    def initialize(self, config: Notification | None = None) -> None:
        """根据设置创建通知管理器"""
        if not self.config.enable:
            logger.info("通知功能已禁用")
            return
        self.notifier = self._get_notifier(config)
        # self.notifier.initialize()

    def _get_notifier(self, config: Notification | None = None) -> Notifier:
        print(f"获取通知器: {config}")
        if config is None:
            config = self.config
        notification_type = config.type
        package_path = f"module.notification.plugin.{notification_type}"
        try:
            notification_module = importlib.import_module(package_path)
        except ImportError as e:
            logger.error(f"加载通知器失败: {notification_type} - {e}")
            notification_module = importlib.import_module("module.notification.plugin.log")
            logger.warning(f"使用默认日志通知器: {notification_module.Notifier.__name__}")
        Notifier = notification_module.Notifier
        logger.debug(f"加载通知器: {config.type}")
        return Notifier(**config.model_dump())

    async def send(self, notify: Message) -> bool:
        """
        发送通知

        Args:
            notify: 通知对象

        Returns:
            bool: 是否发送成功（至少一个通知器成功）
        """
        # 处理通知数据
        processed_notify = await self.processor.process_notification(notify)

        # 发送通知
        result = await self.notifier.post_msg(processed_notify)

        return result


if __name__ == "__main__":
    import asyncio

    from log import setup_logger

    setup_logger(2, reset=True)

    # 测试用例
    title = "败犬"
    link = "posters/aHR0cHM6Ly9pbWFnZS50bWRiLm9yZy90L3Avdzc4MC9wYWRSbWJrMkxkTGd1ZGg1Y0xZMG85VEZ6aEkuanBn"

    title = "AB通知测试"
    link = "https://mikanani.me/images/Bangumi/202507/8a6beaff.jpg"
    nt = Message(title=title, season="1", episode="1", poster_path=link)
    sender = PostNotification()
    sender.initialize()

    async def test():
        success = await sender.send(nt)
        print(f"发送结果: {success}")

    asyncio.run(test())

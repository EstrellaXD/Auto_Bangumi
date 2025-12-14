from models import Message

from .base_notifier import BaseNotifier


class Notifier(BaseNotifier):
    """日志通知器 - 将通知输出到日志"""

    def __init__(self, **kwargs):
        super().__init__()

    def initialize(self) -> None:
        """初始化通知器"""
        pass

    async def post_msg(self, notify: Message) -> bool:
        """输出通知到日志"""
        try:
            message = notify.message
            self.logger.info(f"[Notification] {message}")
            return True

        except Exception as e:
            self.logger.error(f"日志通知输出失败: {e}")
            return False

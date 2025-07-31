from module.models import Notification

from .base_notifier import BaseNotifier


class Notifier(BaseNotifier):
    """日志通知器 - 将通知输出到日志"""
    
    def __init__(self, token: str = "", **kwargs):
        # 日志通知器不需要token，但保持接口一致
        super().__init__(token, **kwargs)
    
    async def post_msg(self, notify: Notification) -> bool:
        """输出通知到日志"""
        try:
            message_data = self.format_message(notify)
            message = message_data["message"] or f"{notify.title} S{notify.season}E{notify.episode}"
            
            self.logger.info(f"[Notification] {message}")
            return True
            
        except Exception as e:
            self.logger.error(f"日志通知输出失败: {e}")
            return False

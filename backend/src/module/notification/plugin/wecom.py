from typing import Dict, Any

from module.models import Notification
from module.network import RequestContent
from module.utils.cache_image import str_to_url

from .base_notifier import BaseNotifier


class Notifier(BaseNotifier):
    """企业微信通知器 - 基于图文消息"""
    
    def __init__(self, token: str, chat_id: str, **kwargs):
        super().__init__(token, **kwargs)
        # chat_id 用作通知URL
        self.notification_url = chat_id
    
    def format_message(self, notify: Notification) -> Dict[str, Any]:
        """格式化企业微信通知消息"""
        data = super().format_message(notify)
        
        # 处理海报路径
        poster_path = notify.poster_path
        if poster_path and "/" in poster_path:
            poster_path = str_to_url(poster_path.split("/")[-1])
        
        # 如果没有海报，使用默认图片 (分辨率: 1068*455)
        if poster_path == "https://mikanani.me" or not poster_path:
            poster_path = "https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png"
        
        # 企业微信标题格式
        title = data["title"]
        if notify.episode:
            title = "【番剧更新】" + title
        
        # 企业微信消息格式
        message = data["message"]
        if poster_path:
            message += f"\n{poster_path}\n".strip()
        
        return {
            **data,
            "title": title,
            "message": message,
            "poster_path": poster_path
        }
    
    async def post_msg(self, notify: Notification) -> bool:
        """发送企业微信通知"""
        try:
            message_data = self.format_message(notify)
            
            data = {
                "key": self.token,
                "type": "news",
                "title": message_data["title"],
                "msg": message_data["message"],
                "picurl": message_data["poster_path"],
            }
            
            async with RequestContent() as req:
                resp = await req.post_data(self.notification_url, data)
                
            self.logger.debug(f"Wecom notification response: {resp.status_code}")
            return resp and resp.status_code == 200
            
        except Exception as e:
            self.logger.error(f"企业微信通知发送失败: {e}")
            return False

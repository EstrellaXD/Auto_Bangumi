import logging

from module.network import RequestContent

logger = logging.getLogger(__name__)


class WecomNotification(RequestContent):
    """企业微信推送 基于图文消息"""

    def __init__(self, token, chat_id, **kwargs):
        super().__init__()
        #Chat_id is used as noti_url in this push tunnel
        self.notification_url = f"{chat_id}"
        self.token = token

    def post_msg(self, text: str) -> bool:
        ##Change message format to match Wecom push better
        info = text.split("：")
        print(info)
        title = "【番剧更新】" + info[1].split("\n")[0].strip()
        msg = info[2].split("\n")[0].strip()+" "+info[3].split("\n")[0].strip()
        picurl = info[3].split("\n")[1].strip()
        #Default pic to avoid blank in message. Resolution:1068*455
        if picurl == "":
            picurl = "https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png"
        data = {
            "key":self.token,                                       
            "type": "news", 
            "title": title,                                                              
            "msg": msg, 
            "picurl":picurl
        }
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Wecom notification: {resp.status_code}")
        return resp.status_code == 200

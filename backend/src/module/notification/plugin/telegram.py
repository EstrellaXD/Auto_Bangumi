import logging

from module.models import Notification
from module.network import RequestContent, load_image

from .base_notifier import Notifier as BaseNotifier

logger = logging.getLogger(__name__)


class Notifier(BaseNotifier):
    def __init__(self, token: str, chat_id: str):
        self.photo_url: str = f"https://api.telegram.org/bot{token}/sendPhoto"
        self.message_url: str = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id: str = chat_id

    def gen_message(self, notify: Notification):
        # notify.message+="\nhello"
        pass

    async def post_msg(self, notify: Notification) -> bool:
        self.gen_message(notify)
        data = {
            "chat_id": self.chat_id,
            "caption": notify.message,
            "text": notify.message,
            "disable_notification": True,
        }
        photo = None
        if notify.poster_path:
            photo = await load_image(notify.poster_path)

        if photo:
            async with RequestContent() as req:
                resp = await req.post_data(self.photo_url, data, files={"photo": photo})
        else:
            async with RequestContent() as req:
                resp = await req.post_data(self.message_url, data)
        logger.debug(f"Telegram notification: {resp.status_code}")
        return resp and resp.status_code == 200

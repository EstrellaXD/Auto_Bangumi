from module.network.request_contents import RequestContent

class TelegramNotification(RequestContent):
    def __init__(self):
        super().__init__()
        self.notification_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def post_msg(self, text: str) -> bool:
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_notification": True,
        }
        resp = self.post_data(self.notification_url, data)
        logger.debug(f"Telegram notification: {resp.status_code}")
        return resp.status_code == 200
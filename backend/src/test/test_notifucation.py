from module.models import Notification
from module.notification.plugin.telegram import TelegramNotification

if __name__ == "__main__":
    pic_url = "https://mikanani.me/images/Bangumi/202304/4b472208.jpg"
    key = ""
    url = f"https://api.telegram.org/bot{key}/sendPhoto"
    id = ""
    data = {
        "chat_id": id,
        "caption": "text",
        "photo": pic_url,
        "disable_notification": True,
    }
    # requests.post(url=url,data=data)
    test_notification = Notification(official_title="成神之日",season = 1,episode = 12,poster_path = pic_url)
    with TelegramNotification(token=key,chat_id= id) as tn:
        tn.post_msg(test_notification)

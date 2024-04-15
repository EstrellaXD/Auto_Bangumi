from module.notification import PostNotification
from module.models import Notification


def test_notification():
    info = Notification(
        official_title="番剧名",
        season=1,
        episode=1,
        poster_path="https://article.biliimg.com/bfs/article/d8bcd0408bf32594fd82f27de7d2c685829d1b2e.png",
    )
    with PostNotification() as notifier:
        assert notifier.send_msg(info) == True


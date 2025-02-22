import asyncio
import importlib
import logging

from module.conf import settings
from module.database import Database
from module.models import Notification
from module.notification.plugin.base_notifier import Notifier as BaseNotifier

logger = logging.getLogger(__name__)


class PostNotification:
    """
    对通知进行处理, 调用 setting 的 notification
    """

    def __init__(self) -> None:
        chat_ids = settings.notification.chat_id.split(",")
        Notifier = self.get_notifier()
        # 支持 多通知帐户
        self.notifier = [
            Notifier(
                token=settings.notification.token,
                chat_id=chat_id,
            )
            for chat_id in chat_ids
        ]

    def parse(self, notify: Notification):
        if notify.episode:
            # Convert episode string to sorted list of integers
            episode_list = sorted(
                [int(e) for e in notify.episode.split(",") if int(e) > 0]
            )

            if not episode_list:
                notify.episode = ""
            else:
                # Build ranges
                ranges = []
                range_start = episode_list[0]
                prev = episode_list[0]

                for num in episode_list[1:] + [None]:
                    if num is None or num != prev + 1:
                        # End of a range
                        range_end = prev
                        if range_start == range_end:
                            ranges.append(str(range_start))
                        else:
                            ranges.append(f"{range_start}-{range_end}")
                        if num is not None:
                            range_start = num
                    prev = num if num is not None else prev

                notify.episode = ",".join(ranges)

            if not notify.poster_path:
                self._get_poster(notify)
            notify.message = f"""
            番剧名称：{notify.title}\n季度： 第{notify.season}季\n更新集数： 第{notify.episode}集
            """.strip()

    @staticmethod
    def _get_poster(notify: Notification):
        """
        有可能传过来的是没有海报的番剧
        比如 collection 的番剧
        获取番剧海报
        """
        with Database() as db:
            bangumi = db.bangumi.search_official_title(notify.title)
        if bangumi:
            notify.poster_path = bangumi.poster_link
        else:
            notify.poster_path = ""

    async def send(self, notify: Notification):
        self.parse(notify)
        try:
            for notifier in self.notifier:
                await notifier.post_msg(notify)
            logger.debug(f"Send notification: {notify.title}")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False

    def get_notifier(self):
        if settings.notification.enable:
            notification_type = settings.notification.type
            package_path = f"module.notification.plugin.{notification_type}"
        else:
            package_path = "module.notification.plugin.log"

        notification: BaseNotifier = importlib.import_module(package_path)
        Notifier = notification.Notifier
        return Notifier


if __name__ == "__main__":
    import asyncio

    from module.conf import setup_logger

    setup_logger("DEBUG", reset=True)

    title = "败犬"
    # link = "posters/aHR0cHM6Ly9pbWFnZS50bWRiLm9yZy90L3Avdzc4MC9wYWRSbWJrMkxkTGd1ZGg1Y0xZMG85VEZ6aEkuanBn"
    nt = Notification(title=title, season=1, episode="1,2,4,5,8", poster_path="")
    asyncio.run(PostNotification().send(nt))

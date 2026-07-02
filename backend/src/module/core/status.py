import time

from module.checker import Checker
from module.conf import LEGACY_DATA_PATH

DOWNLOADER_STATUS_TTL = 60


class ProgramStatus(Checker):
    def __init__(self):
        super().__init__()
        self._downloader_status = False
        self._downloader_last_check: float = 0
        self._tasks_started = False

    @property
    def is_running(self):
        if not self._tasks_started or self.check_first_run():
            return False
        else:
            return True

    @property
    def is_stopped(self):
        return not self._tasks_started

    @property
    def downloader_status(self):
        return self._downloader_status

    async def check_downloader_status(self) -> bool:
        now = time.monotonic()
        if (
            not self._downloader_status
            or (now - self._downloader_last_check) >= DOWNLOADER_STATUS_TTL
        ):
            self._downloader_status = await self.check_downloader()
            self._downloader_last_check = now
        return self._downloader_status

    @property
    def enable_rss(self):
        return self.check_analyser()

    @property
    def enable_renamer(self):
        return self.check_renamer()

    @property
    def first_run(self):
        return self.check_first_run()

    @property
    def legacy_data(self):
        return LEGACY_DATA_PATH.exists()

    @property
    def version_update(self) -> tuple[bool, int | None]:
        is_same, last_minor = self.check_version()
        return not is_same, last_minor

    @property
    def database(self):
        return self.check_database()

    @property
    def img_cache(self):
        return self.check_img_cache()

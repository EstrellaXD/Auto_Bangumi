from pathlib import Path

from module.downloader import Client as DownloadClient


class ProgramStatus:
    @staticmethod
    def check_database() -> bool:
        return Path("data/data.db").exists()

    @staticmethod
    def check_downloader() -> bool:
        return DownloadClient.login_success_event.is_set()

    @staticmethod
    def check_img_cache() -> bool:
        img_path = Path("data/posters")
        if not img_path.exists():
            img_path.mkdir()
            return False
        return True

    @property
    def is_running(self):
        return self.check_downloader()

    @property
    def database(self):
        return self.check_database()

    @property
    def img_cache(self):
        return self.check_img_cache()

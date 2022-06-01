import re
import qbittorrentapi
import logging

from env import EnvInfo

logger = logging.getLogger(__name__)


class qBittorrentRename:
    def __init__(self):
        self.qbt_client = qbittorrentapi.Client(
            host=EnvInfo.host_ip, username=EnvInfo.user_name, password=EnvInfo.password
        )
        try:
            self.qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            logger.exception(e)
        self.recent_info = self.qbt_client.torrents_info(
            status_filter="completed", category="Bangumi"
        )
        self.count = 0
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)
        rules = [
            r"(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
            r"(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
            r"(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)",
            r"(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)",
            r"(.*)第(\d*\.*\d*)话(?:END)?(.*)",
            r"(.*)第(\d*\.*\d*)話(?:END)?(.*)",
            r"(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)",
        ]
        self.rules = [re.compile(rule) for rule in rules]

    def rename_normal(self, name):
        for rule in self.rules:
            matchObj = rule.match(name, re.I)
            if matchObj is not None:
                new_name = f"{matchObj.group(1).strip()} E{matchObj.group(2)}{matchObj.group(3)}"
                return new_name

    def rename_pn(self, name):
        n = re.split(r"\[|\]", name)
        file_name = name.replace(f"[{n[1]}]", "")
        for rule in self.rules:
            matchObj = rule.match(file_name, re.I)
            if matchObj is not None:
                new_name = re.sub(
                    r"\[|\]",
                    "",
                    f"{matchObj.group(1).strip()} E{matchObj.group(2)}{n[-1]}",
                )
                return new_name

    def rename_torrent_file(self, hash, path_name, new_name):
        if path_name != new_name:
            self.qbt_client.torrents_rename_file(
                torrent_hash=hash, old_path=path_name, new_path=new_name
            )
            logger.debug(f"{path_name} >> {new_name}")
            self.count += 1

    def print_result(self):
        logger.debug(f"已完成对{self.torrent_count}个文件的检查")
        logger.debug(f"已对其中{self.count}个文件进行重命名")
        logger.debug(f"完成")

    def run(self):
        method_dict = {"pn": self.rename_pn, "normal": self.rename_normal}
        if EnvInfo.method not in method_dict:
            logger.error(f"error method")
        else:
            for i in range(0, self.torrent_count):
                try:
                    info = self.recent_info[i]
                    name = info.name
                    hash = info.hash
                    path_name = info.content_path.split("/")[-1]
                    new_name = method_dict[EnvInfo.method](name)
                    self.rename_torrent_file(hash, path_name, new_name)
                except:
                    logger.warning(f"{name} rename fail")
            self.print_result()

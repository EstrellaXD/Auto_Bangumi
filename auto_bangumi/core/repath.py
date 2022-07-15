import re
from dataclasses import dataclass
from pathlib import PurePath, PureWindowsPath
from core import DownloadClient
from conf import settings
from utils import json_config


@dataclass
class RuleInfo:
    rule_name: str
    season: int
    folder_name: str


@dataclass
class RePathInfo:
    name: str
    season: int
    hashes: list


class RePath:
    def __init__(self, download_client: DownloadClient):
        self._client = download_client
        self.re_season = re.compile(r"S\d{1,2}")

    @staticmethod
    def get_data() -> list:
        data = json_config.load(settings.info_path)
        return data.get("bangumi_info")

    @staticmethod
    def analyse_path(path: str):
        path_parts = PurePath(path).parts
        folder_name = path_parts[-2]
        season_folder = path_parts[-1]
        season = int(re.search(r"\d{1,2}", season_folder).group())
        return season, folder_name

    def get_rule(self) -> [RuleInfo]:
        rules = self._client.get_download_rules()
        all_rule = []
        for rule in rules:
            path = rules.get(rule).savePath
            season, folder_name = self.analyse_path(path)
            all_rule.append(RuleInfo(rule, season, folder_name))
        return all_rule

    def get_difference(self, bangumi_data: list, rules: list):
        different_data = []
        for rule in rules:
            for item in bangumi_data:
                if item["official_title"] == self.re_season.sub("", rule.rule_name).strip():
                    if item["season"] != rule.season:
                        item["season"] = rule.season
                        item["official_title"] = self.re_season.sub("", rule.rule_name).strip()
                        different_data.append(item)
                    break
        return different_data

    def get_matched_torrents_list(self, difference_data: list) -> [RePathInfo]:
        infos = self._client.get_torrent_info()
        repath_list = []
        for data in difference_data:
            for info in infos:
                if re.search(data["raw_title"], info.name):
                    repath_list.append(RePathInfo(data["name"], data["season"], [info.hash]))
        return repath_list

    def re_path(self, hashes, season):
        old_path = self._client.get_torrent_path(hashes)
        new_path = re.sub(r"Season \d", f"Season {season}", old_path)
        self._client.move_torrent(hashes, new_path)

    # def get_hashes(self):
    def run(self, bangumi_data: list):
        rules = self.get_rule()
        different_data = self.get_difference(bangumi_data, rules)
        repath_list = self.get_matched_torrents_list(different_data)
        for group in repath_list:
            self.re_path(group.hashes, group.season)


if __name__ == '__main__':
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    client = DownloadClient()
    r = RePath(client)
    data = []
    r.run(data)

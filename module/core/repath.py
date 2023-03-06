import logging
import re
from dataclasses import dataclass
from pathlib import PurePath, PureWindowsPath

from module.core import DownloadClient
from module.conf import settings
from module.utils import json_config

logger = logging.getLogger(__name__)


@dataclass
class RuleInfo:
    rule_name: str
    contain: str
    season: int
    folder_name: str
    new_path: str


@dataclass
class RePathInfo:
    path: str
    hashes: list


class RePath:
    def __init__(self, download_client: DownloadClient):
        self._client = download_client
        self.re_season = re.compile(r"S\d{1,2}")

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
            must_contain = rules.get(rule).mustContain
            season, folder_name = self.analyse_path(path)
            new_path = PurePath(settings.download_path, folder_name, f"Season {season}").__str__()
            all_rule.append(RuleInfo(rule, must_contain, season, folder_name, new_path))
        return all_rule

    @staticmethod
    def get_difference(bangumi_data: list, rules: [RuleInfo]) -> [RuleInfo]:
        different_data = []
        for data in bangumi_data:
            for rule in rules:
                rule_name = re.sub(r"S\d", "", rule.rule_name).strip()
                if data.get("official_title") == rule_name:
                    if data.get("season") != rule.season:
                        different_data.append(rule)
                        data["season"] = rule.season
                        break
        return different_data

    def get_matched_torrents_list(self, repath_rules: [RuleInfo]) -> [RePathInfo]:
        infos = self._client.get_torrent_info()
        repath_list = []
        for rule in repath_rules:
            hashes = []
            for info in infos:
                if re.search(rule.contain, info.name):
                    if rule.new_path != info.save_path:
                        hashes.append(info.hash)
                        infos.remove(info)
            if hashes:
                repath_list.append(RePathInfo(rule.new_path, hashes))
        return repath_list

    def re_path(self, repath_info: RePathInfo):
        self._client.move_torrent(repath_info.hashes, repath_info.path)

    def run(self):
        rules = self.get_rule()
        match_list = self.get_matched_torrents_list(rules)
        logging.info(f"Starting repath process.")
        for list in match_list:
            self.re_path(list)

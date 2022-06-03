import os.path
import re

import requests
from qbittorrentapi import Client
from bs4 import BeautifulSoup
import logging

from conf import settings
from const import FULL_SEASON_SUPPORT_GROUP
from downloader import getClient

logger = logging.getLogger(__name__)


class FullSeasonGet:
    def __init__(self, group, bangumi_name, season):
        self.torrents = None
        self.bangumi_name = bangumi_name
        self.group = group
        self.season = season
        self.client = getClient()

    def get_season_rss(self):
        if self.season == "S01":
            season = ""
        else:
            season = self.season
        season = requests.get(
            f"https://mikanani.me/RSS/Search?searchstr={self.group}+{self.bangumi_name}+{season}+1080"
        )
        soup = BeautifulSoup(season.content, "xml")
        self.torrents = soup.find_all("enclosure")

    def add_torrents(self):
        for torrent in self.torrents:
            self.client.torrents_add(
                urls=torrent["url"],
                save_path=str(
                    os.path.join(
                        settings.download_path,
                        re.sub(settings.rule_name_re, " ", self.bangumi_name),
                        self.season)
                ),
                category="Bangumi",
            )

    def run(self):
        if self.group in FULL_SEASON_SUPPORT_GROUP:
            self.get_season_rss()
            self.add_torrents()


if __name__ == "__main__":
    a = FullSeasonGet("Lilith-Raws", "Shijou Saikyou no Daimaou", "S01")
    a.run()
    for torrent in a.torrents:
        logger.debug(torrent["url"])

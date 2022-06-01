import os.path
import requests
from qbittorrentapi import Client
from env import EnvInfo, Other
from bs4 import BeautifulSoup


class FullSeasonGet:
    def __init__(self,group, bangumi_name, season):
        self.torrents = None
        self.bangumi_name = bangumi_name
        self.group = group
        self.season = season

    def get_season_rss(self):
        if self.season == "S01":
            season = ''
        else:
            season = self.season
        season = requests.get(f"https://mikanani.me/RSS/Search?searchstr={self.group}+{self.bangumi_name}+{season}")
        soup = BeautifulSoup(season.content, 'xml')
        self.torrents = soup.find_all('enclosure')

    def add_torrents(self):
        qb = Client(host=EnvInfo.host_ip, username=EnvInfo.user_name, password=EnvInfo.password)
        try:
            qb.auth_log_in()
        except:
            print('Error')
        for torrent in self.torrents:
            qb.torrents_add(
                urls=torrent["url"],
                save_path=str(os.path.join(EnvInfo.download_path, self.bangumi_name, self.season)),
                category="Bangumi",
            )

    def run(self):
        if self.group in Other.full_season_support_group:
            self.get_season_rss()
            self.add_torrents()


if __name__ == "__main__":
    a = FullSeasonGet('Lilith-Raws', 'Shijou Saikyou no Daimaou', 'S01')
    a.run()
    for torrent in a.torrents:
        print(torrent['url'])

import qbittorrentapi
import json
import os


class SetRule:
    def __init__(self, config, info):
        self.bangumi_info = info
        self.rss_link = config["rss_link"]
        self.host_ip = config["host_ip"]
        self.user_name = config["user_name"]
        self.password = config["password"]
        self.qb = qbittorrentapi.Client(host=self.host_ip, username=self.user_name, password=self.password)
        try:
            self.qb.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            print(e)

    def set_rule(self, bangumi_name, season):
        rule = {
            'enable': False,
            'mustContain': bangumi_name,
            'mustNotContain': '720',
            'useRegx': True,
            'episodeFilter': '',
            'smartFilter': False,
            'previouslyMatchedEpisodes': [],
            'affectedFeeds': [self.rss_link],
            'ignoreDays': 0,
            'lastMatch': '',
            'addPaused': False,
            'assignedCategory': 'Bangumi',
            'savePath': os.path.join('/downloads', bangumi_name, season)
            }
        self.qb.rss_set_rule(rule_name=bangumi_name, rule_def=rule)

    def run(self):
        for info in self.bangumi_info:
            self.set_rule(info["title"], info["season"])


import qbittorrentapi
import json
import os


class SetRule:
    def __init__(self):
        with open("config.json") as f:
            info = json.load(f)

        with open("bangumi.json") as f:
            self.bangumi_info = json.load(f)
        self.rss_link = info["rss_link"]
        self.host_ip = "192.168.31.10:8181"
        self.user_name = "admin"
        self.password = "adminadmin"

    def set_rule(self, bangumi_name, season):
        qb = qbittorrentapi.Client(host=self.host_ip, username=self.user_name, password=self.password)
        try:
            qb.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            print(e)
        rule = {
            'enable': False,
            'mustContain': bangumi_name,
            'mustNotContain': '720',
            'useRegx': True,
            'episodeFilter': '',
            'smartFilter': False,
            'previouslyMatchedEpisodes': [],
            'affectedFeeds': [rss_link],
            'ignoreDays': 0,
            'lastMatch': '',
            'addPaused': False,
            'assignedCategory': 'Bangumi',
            'savePath': os.path.join('/downloads', bangumi_name, season)
            }
        qb.rss_set_rule(rule_name=bangumi_name, rule_def=rule)

    def set_rule_main(self):
        for info in self.bangumi_info:
            self.set_rule(info["title"], info["season"])


if __name__ == "__main__":
    rule = SetRule()
    rule.set_rule_main()
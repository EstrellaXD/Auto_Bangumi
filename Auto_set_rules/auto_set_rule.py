import qbittorrentapi
import json
import os

with open("config.json") as f:
    info = json.load(f)

with open("bangumi.json") as f:
    bangumi_info = json.load(f)
rss_link = info["rss_link"]
host_ip = "192.168.31.10:8181"
user_name = "admin"
password = "adminadmin"


def set_rule(bangumi_name, season):
    qb = qbittorrentapi.Client(host=host_ip, username=user_name, password=password)
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

if __name__ == "__main__":
    for info in bangumi_info:
        set_rule(info["title"], info["season"])
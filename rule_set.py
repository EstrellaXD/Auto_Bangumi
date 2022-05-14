# utf-8
import qbittorrentapi
import json
import argparse
import os


def rule_set():
    f = open("config.json")
    server_info = json.load(f)

    host_ip = "http://"+server_info['host_ip']
    user_name = server_info['username']
    password = server_info['password']
    save_path = server_info['savepath']

    qbt_client = qbittorrentapi.Client(host=host_ip, username=user_name, password=password)
    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(e)

    parser = argparse.ArgumentParser(description='Set RSS download rule.')
    parser.add_argument('--name', default='',
                            help='Bangumi Name')
    args = parser.parse_args()
    bangumi_name = args.name
    rule = {'enable':True,
            'mustContain': bangumi_name,
            'mustNotContain': '720',
            'useRegx': True,
            'episodeFilter': '',
            'smartFilter': False,
            'previouslyMatchedEpisodes': [],
            'affectedFeeds': [],
            'ignoreDays': 0,
            'lastMatch': '',
            'addPaused': False,
            'assignedCategory': 'Bangumi',
            'savePath': os.path.join(save_path, bangumi_name)
            }
    qbt_client.rss_set_rule(rule_name=bangumi_name, rule_def=rule)


if __name__ == "__main__":
    rule_set()

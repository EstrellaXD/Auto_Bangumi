import re
import io
import sys
import os.path as op
import qbittorrentapi
import json

f = open("config.json")
server_info = json.load(f)
host_ip = "http://"+server_info['host_ip']
user_name = server_info['username']
password = server_info['password']
log_name = op.join(op.dirname(op.realpath(__file__)), 'log.txt')

# Episode Regular Expression Matching Rules
episode_rules = [r'(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                 r'(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                 r'(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)',
                 r'(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)',
                 r'(.*)第(\d*\.*\d*)话(?:END)?(.*)',
                 r'(.*)第(\d*\.*\d*)話(?:END)?(.*)',
                 r'(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)']
# Suffixs of files we are going to rename
suffixs = ['mp4', 'mkv', 'avi', 'mov', 'flv', 'rmvb', 'ass', 'idx']
sys.stdout = io.TextIOWrapper(buffer=sys.stdout.buffer, encoding='utf8')


class Qbtorrent_Rename:
    def __init__(self):
        self.qbt_client = qbittorrentapi.Client(host=host_ip, username=user_name, password=password)
        try:
            self.qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            print(e)
        self.recent_info = self.qbt_client.torrents_info(status_filter='completed')
        self.hash = None
        self.new_name = None
        self.count = 0
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)

    def rename(self, idx):
        self.name = self.recent_info[idx].name
        n = re.split(r'\[|\]', self.name)
        file_name = self.name.replace(f'[{n[1]}]', '')
        for rule in episode_rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                self.new_name = f'{matchObj.group(1)} E{matchObj.group(2)} {matchObj.group(3)}'

    def qb_rename(self, idx):
        self.rename(idx)
        self.hash = self.recent_info[idx].hash
        try:
            self.qbt_client.torrents_rename_file(torrent_hash=self.hash, old_path=self.name, new_path=self.new_name)
            self.count += 1
            print('{} >> {}'.format(self.name, self.new_name))
        except:
            return
        self.new_name = None


if __name__ == "__main__":
    qb = Qbtorrent_Rename()
    for i in range(0, qb.torrent_count+1):
        try:
            qb.qb_rename(i)
        except:
            print(f"-----已完成对{i+1}个文件的检查，已对其中{qb.count}个文件进行重命名-----")
            print("------------------------完成------------------------")
            quit()

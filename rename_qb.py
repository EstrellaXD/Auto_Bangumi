import argparse
import re
import io
import sys
import os.path as op
import qbittorrentapi
import json

with open("config.json") as f:
    server_info = json.load(f)
host_ip = "http://"+server_info['host_ip']
user_name = server_info['username']
password = server_info['password']
log_name = op.join(op.dirname(op.realpath(__file__)), 'log.txt')
method = server_info['method']

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
parser = argparse.ArgumentParser(description='Regular Expression Match')
parser.add_argument('--hash', default='',
                    help='The torrent Hash value.')
args = parser.parse_args()


class QbittorrentRename:
    def __init__(self, rename_method):
        self.qbt_client = qbittorrentapi.Client(host=host_ip, username=user_name, password=password)
        try:
            self.qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            print(e)
        self.recent_info = self.qbt_client.torrents_info(status_filter='completed')
        self.hash = None
        self.name = None
        self.new_name = None
        self.count = 0
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)
        self.method = rename_method

    def rename_normal(self, idx):
        self.name = self.recent_info[idx].name
        file_name = self.name
        for rule in episode_rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                self.new_name = f'{matchObj.group(1)} E{matchObj.group(2)} {matchObj.group(3)}'

    def rename_pn(self, idx):
        self.name = self.recent_info[idx].name
        n = re.split(r'\[|\]', self.name)
        file_name = self.name.replace(f'[{n[1]}]', '')
        for rule in episode_rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                self.new_name = re.sub(r'\[|\]', '', f'{matchObj.group(1)} E{matchObj.group(2)}.{n[-1]}')

    def rename_hash(self, torrent_hash):
        self.hash = torrent_hash
        try:
            self.qbt_client.torrents_rename_file(torrent_hash=self.hash, old_path=self.name, new_path=self.new_name)
            self.count += 1
            print(f'{self.name} >> {self.new_name}')
        except:
            return

    def rename_app(self):
        if self.method not in ['pn', 'normal', 'hash']:
            print('error method')
        elif self.method == 'normal':
            for i in range(0, self.torrent_count + 1):
                try:
                    self.rename_normal(i)
                except:
                    print(f"-----已完成对{i + 1}个文件的检查，已对其中{self.count}个文件进行重命名-----")
                    print("------------------------完成------------------------")
                    quit()
        elif self.method == 'pn':
            for i in range(0, self.torrent_count + 1):
                try:
                    self.rename_pn(i)
                except:
                    print(f"-----已完成对{i + 1}个文件的检查，已对其中{self.count}个文件进行重命名-----")
                    print("------------------------完成------------------------")
                    quit()
        elif self.method == 'hash':
            self.rename_hash(args.hash)


if __name__ == "__main__":
    rename = QbittorrentRename(method)
    rename.rename_app()

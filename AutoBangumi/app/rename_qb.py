import re
import sys
import qbittorrentapi
import time
from env import EnvInfo


class qBittorrentRename:
    def __init__(self):
        self.qbt_client = qbittorrentapi.Client(host=EnvInfo.host_ip,
                                                username=EnvInfo.user_name,
                                                password=EnvInfo.password)
        try:
            self.qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            print(e)
        self.recent_info = self.qbt_client.torrents_info(status_filter='completed')
        self.hash = None
        self.name = None
        self.new_name = None
        self.path_name = None
        self.count = 0
        self.rename_count = 0
        self.torrent_count = len(self.recent_info)
        self.rules = [r'(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                      r'(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)',
                      r'(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)',
                      r'(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)',
                      r'(.*)第(\d*\.*\d*)话(?:END)?(.*)',
                      r'(.*)第(\d*\.*\d*)話(?:END)?(.*)',
                      r'(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)']

    def rename_normal(self, idx):
        self.name = self.recent_info[idx].name
        self.hash = self.recent_info[idx].hash
        self.path_name = self.recent_info[idx].content_path.split("/")[-1]
        file_name = self.name
        for rule in self.rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                self.new_name = f'{matchObj.group(1).strip()} E{matchObj.group(2)}{matchObj.group(3)}'

    def rename_pn(self, idx):
        self.name = self.recent_info[idx].name
        self.hash = self.recent_info[idx].hash
        self.path_name = self.recent_info[idx].content_path.split("/")[-1]
        n = re.split(r'\[|\]', self.name)
        file_name = self.name.replace(f'[{n[1]}]', '')
        for rule in self.rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                self.new_name = re.sub(r'\[|\]', '', f'{matchObj.group(1).strip()} E{matchObj.group(2)}{n[-1]}')

    def rename(self):
        if self.path_name != self.new_name:
            self.qbt_client.torrents_rename_file(torrent_hash=self.hash, old_path=self.path_name, new_path=self.new_name)
            sys.stdout.write(f"[{time.strftime('%Y-%m-%d %X')}]  {self.path_name} >> {self.new_name}")
            self.count += 1
        else:
            return

    def clear_info(self):
        self.name = None
        self.hash = None
        self.new_name = None
        self.path_name = None

    def print_result(self):
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  已完成对{self.torrent_count}个文件的检查" + '\n')
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  已对其中{self.count}个文件进行重命名" + '\n')
        sys.stdout.write(f"[{EnvInfo.time_show_obj}]  完成" + '\n')
        sys.stdout.flush()

    def run(self):
        if EnvInfo.method not in ['pn', 'normal']:
            print('error method')
        elif EnvInfo.method == 'normal':
            for i in range(0, self.torrent_count + 1):
                try:
                    self.rename_normal(i)
                    self.rename()
                    self.clear_info()
                except:
                    self.print_result()
        elif EnvInfo.method == 'pn':
            for i in range(0, self.torrent_count + 1):
                try:
                    self.rename_pn(i)
                    self.rename()
                    self.clear_info()
                except:
                    self.print_result()




import re
import io
import sys
import os.path as op
import argparse
import qbittorrentapi



host_ip = '192.168.31.10:8181'
user_name = 'admin'
password = 'adminadmin'
log_name=op.join(op.dirname(op.realpath(__file__)), 'log.txt')

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
sys.stdout = io.TextIOWrapper(buffer=sys.stdout.buffer,encoding='utf8')

# Parse the input arguments. You can whether input only root, or only path, or both root and name.
parser = argparse.ArgumentParser(description='Regular Expression Match')
parser.add_argument('--hash', default='',
                    help='The torrent Hash value.')


class Qbtorrent_Rename:
    def __init__(self, hash):
        self.qbt_client = qbittorrentapi.Client(host=host_ip, username=user_name, password=password)
        try:
            self.qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            print(e)
        self.hash = hash
        recent_info = self.qbt_client.torrents_info(hashes=self.hash)
        self.name = recent_info[0].name
        self.new_name = None

    def rename(self):
        for rule in episode_rules:
            matchObj = re.match(rule, self.name, re.I)
            if matchObj is not None:
                self.new_name = f'{matchObj.group(1)} E{matchObj.group(2)} {matchObj.group(3)}'

    def qb_rename(self):
        self.rename()
        try:
            self.qbt_client.torrents_rename_file(torrent_hash=self.hash, old_path=self.name, new_path=self.new_name)
            print('{} >> {}'.format(self.name, self.new_name))
        except:
            print('file exits')
            return


if __name__ == "__main__":
    args = parser.parse_args()
    qb = Qbtorrent_Rename(args.hash)
    qb.qb_rename()
